import asyncio
import numpy as np

from my_config import (
    EMB_MODEL,
    EMB_API_KEY,
    EMB_BASE_URL,
    EMB_DIM,
)

from hyperrag.llm import openai_embedding


async def main():
    texts = [
        "Hyper-RAG is a retrieval augmented generation system.",
        "This is a second sentence used for testing embeddings.",
    ]

    embeddings = await openai_embedding(
        texts,
        model=EMB_MODEL,
        api_key=EMB_API_KEY,
        base_url=EMB_BASE_URL,
    )

    print("Number of texts:", len(texts))
    print("Embedding array shape:", embeddings.shape)
    print("First vector dimension:", len(embeddings[0]))
    print("Data type:", embeddings.dtype)

    assert isinstance(embeddings, np.ndarray), "Output must be a numpy ndarray"
    assert embeddings.shape == (2, 1024), f"Expected shape (2, 1024), got {embeddings.shape}"
    assert len(embeddings[0]) == 1024, f"Expected 1024 dimensions, got {len(embeddings[0])}"
    assert embeddings.dtype == np.float32, f"Expected float32, got {embeddings.dtype}"
    print("Embedding test PASSED: 1024 dimensions verified.")


if __name__ == "__main__":
    asyncio.run(main())