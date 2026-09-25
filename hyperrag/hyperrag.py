import os
import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Type, cast, Optional, Any, Tuple, Dict

from .operate import (
    chunking_by_token_size,
    extract_entities,
    hyper_query_lite,
    hyper_query,
    naive_query,
    graph_query,
    llm_query,
)
from .llm import (
    gpt_4o_mini_complete,
    openai_embedding,
)

from .storage import (
    JsonKVStorage,
    NanoVectorDBStorage,
    HypergraphStorage,
)


from .utils import (
    EmbeddingFunc,
    compute_mdhash_id,
    limit_async_func_call,
    convert_response_to_json,
    logger,
    set_logger,
    limit_async_gen_call
)
from .base import (
    BaseKVStorage,
    BaseVectorStorage,
    StorageNameSpace,
    QueryParam,
    BaseHypergraphStorage,
)

from .operate import (
    hyper_query_stream,
    hyper_query_lite_stream,
    naive_query_stream,
    llm_query_stream,
    hyper_retrieve_lite,
    hyper_query_lite_reasoning,
    hyper_query_lite_stream_from_context,
)
from .adaptive_router import AdaptiveRouter, AdaptiveDecision
from .retrieval_sufficiency import RetrievalSufficiencyEvaluator, RetrievalSufficiency
from my_config import (
    ADAPTIVE_RAG_ENABLED,
    ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED,
    ADAPTIVE_LOG_DECISIONS,
)


def always_get_an_event_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_event_loop()

    except RuntimeError:
        logger.info("Creating a new event loop in main thread.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        return loop


@dataclass
class HyperRAG:
    working_dir: str = field(
        default_factory=lambda: f"./HyperRAG_cache_{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
    )
    # print(working_dir)

    current_log_level = logger.level
    log_level: str = field(default=current_log_level)

    # text chunking
    chunk_token_size: int = 1200
    chunk_overlap_token_size: int = 100
    tiktoken_model_name: str = "gpt-4o-mini"

    # entity extraction
    entity_extract_max_gleaning: int = 1
    entity_summary_to_max_tokens: int = 500
    entity_additional_properties_to_max_tokens: int = 250
    relation_summary_to_max_tokens: int = 750
    relation_keywords_to_max_tokens: int = 100

    embedding_func: EmbeddingFunc = field(default_factory=lambda: openai_embedding)
    embedding_batch_num: int = 8
    embedding_func_max_async: int = 16

    # LLM
    llm_model_func: callable = gpt_4o_mini_complete  # hf_model_complete#
    # llm_model_name: str = "meta-llama/Llama-3.2-1B-Instruct"  #'meta-llama/Llama-3.2-1B'#'google/gemma-2-2b-it'
    llm_model_name: str = ""
    llm_model_max_token_size: int = 32768
    llm_model_max_async: int = 16
    llm_model_kwargs: dict = field(default_factory=dict)

    llm_model_stream_func: callable = None

    # storage
    key_string_value_json_storage_cls: Type[BaseKVStorage] = JsonKVStorage
    vector_db_storage_cls: Type[BaseVectorStorage] = NanoVectorDBStorage
    vector_db_storage_cls_kwargs: dict = field(default_factory=dict)
    hypergraph_storage_cls: Type[BaseHypergraphStorage] = HypergraphStorage
    enable_llm_cache: bool = True

    # extension
    addon_params: dict = field(default_factory=dict)
    convert_response_to_json_func: callable = convert_response_to_json

    # adaptive routing & sufficiency evaluation
    adaptive_router: Optional[Any] = None
    sufficiency_evaluator: Optional[Any] = None

    def __post_init__(self):
        log_file = os.path.join(self.working_dir, "HyperRAG.log")
        set_logger(log_file)
        logger.setLevel(self.log_level)

        if self.adaptive_router is None:
            self.adaptive_router = AdaptiveRouter()
        if self.sufficiency_evaluator is None:
            self.sufficiency_evaluator = RetrievalSufficiencyEvaluator()
        self.last_adaptive_decision: Optional[AdaptiveDecision] = None

        logger.info(f"Logger initialized for working directory: {self.working_dir}")

        _print_config = ",\n  ".join([f"{k} = {v}" for k, v in asdict(self).items()])
        logger.debug(f"HyperRAG init with param:\n  {_print_config}\n")

        if not os.path.exists(self.working_dir):
            logger.info(f"Creating working directory {self.working_dir}")
            os.makedirs(self.working_dir)

        self.full_docs = self.key_string_value_json_storage_cls(
            namespace="full_docs", global_config=asdict(self)
        )

        self.text_chunks = self.key_string_value_json_storage_cls(
            namespace="text_chunks", global_config=asdict(self)
        )

        self.llm_response_cache = (
            self.key_string_value_json_storage_cls(
                namespace="llm_response_cache", global_config=asdict(self)
            )
            if self.enable_llm_cache
            else None
        )
        """
            download from hgdb_path
        """
        self.chunk_entity_relation_hypergraph = self.hypergraph_storage_cls(
            namespace="chunk_entity_relation", global_config=asdict(self)
        )

        self.embedding_func = limit_async_func_call(self.embedding_func_max_async)(
            self.embedding_func
        )

        self.entities_vdb = self.vector_db_storage_cls(
            namespace="entities",
            global_config=asdict(self),
            embedding_func=self.embedding_func,
            meta_fields={"entity_name"},
        )
        self.relationships_vdb = self.vector_db_storage_cls(
            namespace="relationships",
            global_config=asdict(self),
            embedding_func=self.embedding_func,
            meta_fields={"id_set"},
        )
        self.chunks_vdb = self.vector_db_storage_cls(
            namespace="chunks",
            global_config=asdict(self),
            embedding_func=self.embedding_func,
        )

        self.llm_model_func = limit_async_func_call(self.llm_model_max_async)(
            partial(
                self.llm_model_func,
                hashing_kv=self.llm_response_cache,
                **self.llm_model_kwargs,
            )
        )

        if getattr(self, "llm_model_stream_func", None) is not None:
            # 先把 hashing_kv 注入到 stream func（供 openai_complete_stream_if_cache 使用）
            self.llm_model_stream_func = limit_async_gen_call(self.llm_model_max_async)(
                partial(
                    self.llm_model_stream_func,
                    hashing_kv=self.llm_response_cache,
                    **self.llm_model_kwargs,
                )
            )

    def insert(self, string_or_strings):
        loop = always_get_an_event_loop()
        return loop.run_until_complete(self.ainsert(string_or_strings))

    async def ainsert(self, string_or_strings):
        try:
            if isinstance(string_or_strings, str):
                string_or_strings = [string_or_strings]

            new_docs = {
                compute_mdhash_id(c.strip(), prefix="doc-"): {"content": c.strip()}
                for c in string_or_strings
            }
            _add_doc_keys = await self.full_docs.filter_keys(list(new_docs.keys()))
            new_docs = {k: v for k, v in new_docs.items() if k in _add_doc_keys}
            if not len(new_docs):
                logger.warning("All docs are already in the storage")
                return
            # ----------------------------------------------------------------------------
            logger.info(f"[New Docs] inserting {len(new_docs)} docs")

            inserting_chunks = {}
            for doc_key, doc in new_docs.items():
                chunks = {
                    compute_mdhash_id(dp["content"], prefix="chunk-"): {
                        **dp,
                        "full_doc_id": doc_key,
                    }
                    for dp in chunking_by_token_size(
                        doc["content"],
                        overlap_token_size=self.chunk_overlap_token_size,
                        max_token_size=self.chunk_token_size,
                        tiktoken_model=self.tiktoken_model_name,
                    )
                }
                inserting_chunks.update(chunks)
            _add_chunk_keys = await self.text_chunks.filter_keys(
                list(inserting_chunks.keys())
            )
            inserting_chunks = {
                k: v for k, v in inserting_chunks.items() if k in _add_chunk_keys
            }
            if not len(inserting_chunks):
                logger.warning("All chunks are already in the storage")
                return
            # ----------------------------------------------------------------------------
            logger.info(f"[New Chunks] inserting {len(inserting_chunks)} chunks")

            await self.chunks_vdb.upsert(inserting_chunks)
            # ----------------------------------------------------------------------------
            logger.info("[Entity Extraction]...")
            maybe_new_kg = await extract_entities(
                inserting_chunks,
                knowledge_hypergraph_inst=self.chunk_entity_relation_hypergraph,
                entity_vdb=self.entities_vdb,
                relationships_vdb=self.relationships_vdb,
                global_config=asdict(self),
            )
            if maybe_new_kg is None:
                logger.warning("No new entities and relationships found")
                return
            # ----------------------------------------------------------------------------
            self.chunk_entity_relation_hypergraph = maybe_new_kg
            await self.full_docs.upsert(new_docs)
            await self.text_chunks.upsert(inserting_chunks)
        finally:
            await self._insert_done()

    async def _insert_done(self):
        tasks = []
        for storage_inst in [
            self.full_docs,
            self.text_chunks,
            self.llm_response_cache,
            self.entities_vdb,
            self.relationships_vdb,
            self.chunks_vdb,
            self.chunk_entity_relation_hypergraph,
        ]:
            if storage_inst is None:
                continue
            tasks.append(cast(StorageNameSpace, storage_inst).index_done_callback())
        await asyncio.gather(*tasks)

    def _resolve_query_mode(
        self, query: str, param: QueryParam
    ) -> Tuple[str, Optional[AdaptiveDecision]]:
        """
        Resolve the effective execution mode (hyper, hyper-lite, graph, naive, llm)
        handling direct aliases ('core', 'lite') and 'adaptive' routing.
        Preserves direct mode execution while enabling adaptive selection.
        """
        raw_mode = (param.mode or "adaptive").lower().strip()

        # Direct explicit mode mappings
        if raw_mode in ("hyper", "core"):
            return "hyper", None
        elif raw_mode in ("hyper-lite", "lite"):
            return "hyper-lite", None
        elif raw_mode == "hyper-query":
            return "hyper", None
        elif raw_mode in ("graph", "naive", "llm"):
            return raw_mode, None
        elif raw_mode == "adaptive":
            if not ADAPTIVE_RAG_ENABLED:
                logger.info("[Adaptive RAG] Disabled in config, falling back to core (hyper) mode")
                return "hyper", None

            if self.adaptive_router is None:
                self.adaptive_router = AdaptiveRouter()

            decision = self.adaptive_router.route(query)
            effective_mode = "hyper" if decision.mode == "core" else "hyper-lite"
            return effective_mode, decision
        else:
            raise ValueError(f"Unknown mode {param.mode}")

    def query(self, query: str, param: QueryParam = QueryParam()):
        loop = always_get_an_event_loop()
        return loop.run_until_complete(self.aquery(query, param))

    async def aquery(self, query: str, param: QueryParam = QueryParam()):
        effective_mode, decision = self._resolve_query_mode(query, param)
        self.last_adaptive_decision = decision
        if decision is not None:
            param.adaptive_decision = decision

        # Adaptive Mode with Retrieval Sufficiency & Escalation
        if decision is not None and effective_mode == "hyper-lite" and ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED:
            if self.sufficiency_evaluator is None:
                self.sufficiency_evaluator = RetrievalSufficiencyEvaluator()

            # Step 1: Perform Lite retrieval only (avoiding LLM reasoning upfront)
            entity_context, entity_keywords = await hyper_retrieve_lite(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )

            # Step 2: Evaluate retrieval sufficiency
            suff = self.sufficiency_evaluator.evaluate(
                query,
                entity_context,
                features=decision.features,
                complexity_score=decision.score,
            )
            decision.retrieval_sufficiency_score = suff.score
            decision.retrieval_sufficient = suff.sufficient
            decision.retrieval_metrics = suff.metrics

            if not suff.sufficient:
                # Step 3: Escalate Lite -> Core
                decision.escalated = True
                decision.final_mode = "core"
                decision.mode = "core"
                decision.escalation_reason = (
                    suff.reasons[0] if suff.reasons else "Insufficient retrieval evidence"
                )

                if ADAPTIVE_LOG_DECISIONS:
                    log_msg = (
                        f"[Adaptive RAG]\n"
                        f"Retrieval sufficiency score: {suff.score}\n"
                        f"Status: INSUFFICIENT\n\n"
                        f"[Adaptive RAG]\n"
                        f"Escalating LITE -> CORE\n"
                        f"Reason: {decision.escalation_reason}"
                    )
                    logger.info(log_msg)
                    print(log_msg)

                # Execute Core retrieval and reasoning
                response = await hyper_query(
                    query,
                    self.chunk_entity_relation_hypergraph,
                    self.entities_vdb,
                    self.relationships_vdb,
                    self.text_chunks,
                    param,
                    asdict(self),
                )
            else:
                # Lite retrieval is sufficient: run Lite reasoning with already retrieved context
                decision.final_mode = "lite"
                decision.escalated = False

                if ADAPTIVE_LOG_DECISIONS:
                    log_msg = (
                        f"[Adaptive RAG]\n"
                        f"Initial mode: LITE\n"
                        f"Retrieval sufficiency score: {suff.score}\n"
                        f"Status: SUFFICIENT\n"
                        f"No escalation required"
                    )
                    logger.info(log_msg)
                    print(log_msg)

                response = await hyper_query_lite_reasoning(
                    query,
                    entity_context,
                    entity_keywords,
                    param,
                    asdict(self),
                )

        elif decision is not None and effective_mode == "hyper":
            decision.final_mode = "core"
            decision.escalated = False
            if ADAPTIVE_LOG_DECISIONS:
                log_msg = (
                    "[Adaptive RAG]\n"
                    "Initial mode: CORE\n"
                    "Skipping Lite sufficiency check"
                )
                logger.info(log_msg)
                print(log_msg)

            response = await hyper_query(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.relationships_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )

        elif effective_mode == "hyper":
            response = await hyper_query(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.relationships_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )
        elif effective_mode == "hyper-lite":
            response = await hyper_query_lite(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )
        elif effective_mode == "graph":
            response = await graph_query(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.relationships_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )
        elif effective_mode == "naive":
            response = await naive_query(
                query,
                self.chunks_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )
        elif effective_mode == "llm":
            response = await llm_query(
                query,
                param,
                asdict(self),
            )
        else:
            raise ValueError(f"Unknown mode {param.mode}")

        await self._query_done()

        if param.return_type == "json" and isinstance(response, dict) and decision is not None:
            response["adaptive_decision"] = decision.to_dict()

        return response

    async def astream_query(self, query: str, param: QueryParam = QueryParam()):
        """
        流式查询：返回 async generator（逐 token / 逐块）
        依赖 self.llm_model_stream_func，不提供则抛错。
        """
        if self.llm_model_stream_func is None:
            raise AttributeError("llm_model_stream_func is not set, streaming is unavailable.")

        effective_mode, decision = self._resolve_query_mode(query, param)
        self.last_adaptive_decision = decision
        if decision is not None:
            param.adaptive_decision = decision

        # 把 stream func 放进 global_config
        cfg = asdict(self)
        cfg["llm_model_stream_func"] = self.llm_model_stream_func

        if decision is not None and effective_mode == "hyper-lite" and ADAPTIVE_RETRIEVAL_SUFFICIENCY_ENABLED:
            if self.sufficiency_evaluator is None:
                self.sufficiency_evaluator = RetrievalSufficiencyEvaluator()

            entity_context, entity_keywords = await hyper_retrieve_lite(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.text_chunks,
                param,
                cfg,
            )

            suff = self.sufficiency_evaluator.evaluate(
                query,
                entity_context,
                features=decision.features,
                complexity_score=decision.score,
            )
            decision.retrieval_sufficiency_score = suff.score
            decision.retrieval_sufficient = suff.sufficient
            decision.retrieval_metrics = suff.metrics

            if not suff.sufficient:
                decision.escalated = True
                decision.final_mode = "core"
                decision.mode = "core"
                decision.escalation_reason = (
                    suff.reasons[0] if suff.reasons else "Insufficient retrieval evidence"
                )

                if ADAPTIVE_LOG_DECISIONS:
                    log_msg = (
                        f"[Adaptive RAG]\n"
                        f"Retrieval sufficiency score: {suff.score}\n"
                        f"Status: INSUFFICIENT\n\n"
                        f"[Adaptive RAG]\n"
                        f"Escalating LITE -> CORE\n"
                        f"Reason: {decision.escalation_reason}"
                    )
                    logger.info(log_msg)
                    print(log_msg)

                async for tok in hyper_query_stream(
                    query,
                    self.chunk_entity_relation_hypergraph,
                    self.entities_vdb,
                    self.relationships_vdb,
                    self.text_chunks,
                    param,
                    cfg,
                ):
                    yield tok
            else:
                decision.final_mode = "lite"
                decision.escalated = False

                if ADAPTIVE_LOG_DECISIONS:
                    log_msg = (
                        f"[Adaptive RAG]\n"
                        f"Initial mode: LITE\n"
                        f"Retrieval sufficiency score: {suff.score}\n"
                        f"Status: SUFFICIENT\n"
                        f"No escalation required"
                    )
                    logger.info(log_msg)
                    print(log_msg)

                async for tok in hyper_query_lite_stream_from_context(
                    query,
                    entity_context,
                    entity_keywords,
                    param,
                    cfg,
                ):
                    yield tok

        elif decision is not None and effective_mode == "hyper":
            decision.final_mode = "core"
            decision.escalated = False
            if ADAPTIVE_LOG_DECISIONS:
                log_msg = (
                    "[Adaptive RAG]\n"
                    "Initial mode: CORE\n"
                    "Skipping Lite sufficiency check"
                )
                logger.info(log_msg)
                print(log_msg)

            async for tok in hyper_query_stream(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.relationships_vdb,
                self.text_chunks,
                param,
                cfg,
            ):
                yield tok

        elif effective_mode == "hyper":
            async for tok in hyper_query_stream(
                    query,
                    self.chunk_entity_relation_hypergraph,
                    self.entities_vdb,
                    self.relationships_vdb,
                    self.text_chunks,
                    param,
                    cfg,
            ):
                yield tok

        elif effective_mode == "hyper-lite":
            async for tok in hyper_query_lite_stream(
                    query,
                    self.chunk_entity_relation_hypergraph,
                    self.entities_vdb,
                    self.text_chunks,
                    param,
                    cfg,
            ):
                yield tok

        elif effective_mode == "naive":
            async for tok in naive_query_stream(
                    query,
                    self.chunks_vdb,
                    self.text_chunks,
                    param,
                    cfg,
            ):
                yield tok

        elif effective_mode == "llm":
            async for tok in llm_query_stream(query, param, cfg):
                yield tok

        else:
            raise ValueError(f"Unknown mode {param.mode}")

        await self._query_done()


    async def _query_done(self):
        tasks = []
        for storage_inst in [self.llm_response_cache]:
            if storage_inst is None:
                continue
            tasks.append(cast(StorageNameSpace, storage_inst).query_done_callback())
        await asyncio.gather(*tasks)
