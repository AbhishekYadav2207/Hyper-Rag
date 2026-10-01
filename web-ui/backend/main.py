from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
try:
    from .db import get_hypergraph, getFrequentVertices, get_vertices, get_hyperedges, get_vertice, get_vertice_neighbor, get_hyperedge_neighbor_server, add_vertex, add_hyperedge, delete_vertex, delete_hyperedge, update_vertex, update_hyperedge, get_hyperedge_detail, db_manager
    from .file_manager import file_manager
except (ImportError, ValueError):
    from db import get_hypergraph, getFrequentVertices, get_vertices, get_hyperedges, get_vertice, get_vertice_neighbor, get_hyperedge_neighbor_server, add_vertex, add_hyperedge, delete_vertex, delete_hyperedge, update_vertex, update_hyperedge, get_hyperedge_detail, db_manager
    from file_manager import file_manager
import json
import os
import asyncio
import numpy as np
import logging
import sys
import importlib.util
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from io import StringIO

# Add HyperRAG related imports
# If not importable, look upward for directory containing hyperrag and add to sys.path
if importlib.util.find_spec("hyperrag") is None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "hyperrag" / "__init__.py").exists():
            sys.path.insert(0, str(parent))  # Note: parent directory, not .../hyperrag
            break

try:
    from hyperrag import HyperRAG, QueryParam
    from hyperrag.utils import EmbeddingFunc
    from hyperrag.llm import openai_embedding, openai_complete_if_cache
    HYPERRAG_AVAILABLE = True
except ImportError as e:
    print(f"HyperRAG not available: {e}")
    HYPERRAG_AVAILABLE = False

try:
    from hyperrag.ingestion import (
        GenericIngestionPipeline,
        IngestionConfig,
        DatasetInspectionReport,
        sanitize_database_name,
        SUPPORTED_EXTENSIONS,
    )
    GENERIC_INGESTION_AVAILABLE = True
except ImportError as e:
    print(f"Generic Ingestion not available: {e}")
    GENERIC_INGESTION_AVAILABLE = False


# Set file paths and canonical settings store
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_backend_dir))
SETTINGS_FILE = os.path.join(_repo_root, "settings.json")
_legacy_settings = os.path.join(_backend_dir, "settings.json")
if not os.path.exists(SETTINGS_FILE) and os.path.exists(_legacy_settings):
    try:
        import shutil
        shutil.copy2(_legacy_settings, SETTINGS_FILE)
    except Exception:
        pass

def init_runtime_environment():
    """Ensure essential runtime storage directories exist."""
    dirs_to_init = [
        os.path.join(_repo_root, "caches"),
        os.path.join(_repo_root, "hyperrag_cache"),
        os.path.join(_repo_root, "uploads"),
        os.path.join(_repo_root, "scratch"),
        os.path.join(_backend_dir, "uploads"),
    ]
    for d in dirs_to_init:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass

init_runtime_environment()

import re

def sanitize_error_message(msg: str) -> str:
    """Sanitize error messages to prevent exposing API keys or auth headers."""
    if not msg:
        return ""
    text = str(msg)
    text = re.sub(r'Bearer\s+[A-Za-z0-9_\-\.]+', 'Bearer [REDACTED]', text, flags=re.IGNORECASE)
    text = re.sub(r'Authorization:\s*[^\s]+', 'Authorization: [REDACTED]', text, flags=re.IGNORECASE)
    text = re.sub(r'sk-[A-Za-z0-9_\-\.]{8,}', '[REDACTED_API_KEY]', text)
    text = re.sub(r'key-[A-Za-z0-9_\-\.]{8,}', '[REDACTED_API_KEY]', text)
    return text

def mask_key(key: Optional[str]) -> str:
    """Return masked representation of an API key, e.g. ••••••••••••abcd."""
    if not key or not isinstance(key, str):
        return ""
    stripped = key.strip()
    if not stripped:
        return ""
    if len(stripped) <= 8:
        return "••••••••"
    return f"••••••••••••{stripped[-4:]}"

def load_raw_settings() -> dict:
    """Load settings from SETTINGS_FILE directly without exposing in API."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    return saved
        except Exception as e:
            main_logger.warning(f"Error reading {SETTINGS_FILE}: {e}")
    return {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup frontend static assets
frontend_dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
frontend_assets_dir = os.path.join(frontend_dist_dir, "assets")

if os.path.exists(frontend_assets_dir):
    app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="assets")

@app.get("/logo.png")
async def serve_logo():
    logo_file = os.path.join(frontend_dist_dir, "logo.png")
    if os.path.exists(logo_file):
        return FileResponse(logo_file)
    raise HTTPException(status_code=404, detail="Logo not found")

@app.get("/")
async def root():
    index_file = os.path.join(frontend_dist_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Hyper-RAG", "status": "Frontend not built. Please run 'npm run build' inside web-ui/frontend or use start script."}

@app.get("/health")
async def health_check():
    """
    Application health and readiness check endpoint.
    Exposes non-sensitive status without revealing credentials or internal secrets.
    """
    settings = get_effective_settings()
    llm_configured = bool(settings.get("apiKey") or os.getenv("OPENROUTER_API_KEYS") or os.getenv("OPENROUTER_API_KEY"))
    emb_configured = bool(settings.get("embeddingApiKey") or os.getenv("EMB_API_KEYS") or os.getenv("EMB_API_KEY") or os.getenv("MISTRAL_API_KEY"))
    
    return {
        "status": "healthy",
        "backend": "ready",
        "hyperrag_available": HYPERRAG_AVAILABLE,
        "generic_ingestion_available": GENERIC_INGESTION_AVAILABLE,
        "llm_provider_configured": llm_configured,
        "embedding_provider_configured": emb_configured,
        "llm_model": settings.get("modelName", "unknown"),
        "embedding_model": settings.get("embeddingModel", "unknown"),
        "version": "1.0.0"
    }


@app.get("/db")
async def db(database: str = None):
    """
    Get full hypergraph data JSON
    """
    try:
        data = get_hypergraph(database)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/vertices")
async def get_vertices_function(database: str = None, page: int = None, page_size: int = None):
    """
    Get vertices list
    """
    try:
        data = getFrequentVertices(database, page, page_size)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/hyperedges")
async def get_hypergraph_function(database: str = None, page: int = None, page_size: int = None):
    """
    Get hyperedges list
    """
    try:
        data = get_hyperedges(database, page, page_size)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/hyperedges/{hyperedge_id}")
async def get_hyperedge(hyperedge_id: str, database: str = None):
    """
    Get details of specified hyperedge
    """
    try:
        hyperedge_id = hyperedge_id.replace("%20", " ")
        vertices = hyperedge_id.split("|*|")
        data = get_hyperedge_detail(vertices, database)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/vertices/{vertex_id}")
async def get_vertex(vertex_id: str, database: str = None):
    """
    Get specified vertex JSON
    """
    vertex_id = vertex_id.replace("%20", " ")
    try:
        data = get_vertice(vertex_id, database)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/vertices_neighbor/{vertex_id}")
async def get_vertex_neighbor(vertex_id: str, database: str = None):
    """
    Get neighbors of specified vertex
    """
    vertex_id = vertex_id.replace("%20", " ")
    try:
        data = get_vertice_neighbor(vertex_id, database)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/hyperedge_neighbor/{hyperedge_id}")
async def get_hyperedge_neighbor(hyperedge_id: str, database: str = None):
    """
    Get neighbors of specified hyperedge
    """
    hyperedge_id = hyperedge_id.replace("%20", " ")
    hyperedge_id = hyperedge_id.replace("*", "#")
    print(hyperedge_id)
    try:
        data = get_hyperedge_neighbor_server(hyperedge_id, database)
        return data
    except Exception as e:
        return {"error": str(e)}

class VertexModel(BaseModel):
    vertex_id: str
    entity_name: str = ""
    entity_type: str = ""
    description: str = ""
    additional_properties: str = ""
    database: str = None

class HyperedgeModel(BaseModel):
    vertices: list
    keywords: str = ""
    summary: str = ""
    database: str = None

class VertexUpdateModel(BaseModel):
    entity_name: str = ""
    entity_type: str = ""
    description: str = ""
    additional_properties: str = ""
    database: str = None

class HyperedgeUpdateModel(BaseModel):
    keywords: str = ""
    summary: str = ""
    database: str = None

@app.post("/db/vertices")
async def create_vertex(vertex: VertexModel):
    """
    Create new vertex
    """
    try:
        result = add_vertex(vertex.vertex_id, {
            "entity_name": vertex.entity_name,
            "entity_type": vertex.entity_type,
            "description": vertex.description,
            "additional_properties": vertex.additional_properties
        }, vertex.database)
        return {"success": True, "message": "Vertex created successfully", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/db/hyperedges")
async def create_hyperedge(hyperedge: HyperedgeModel):
    """
    Create new hyperedge
    """
    try:
        result = add_hyperedge(hyperedge.vertices, {
            "keywords": hyperedge.keywords,
            "summary": hyperedge.summary
        }, hyperedge.database)
        return {"success": True, "message": "Hyperedge created successfully", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.put("/db/vertices/{vertex_id}")
async def update_vertex_endpoint(vertex_id: str, vertex: VertexUpdateModel):
    """
    Update vertex information
    """
    try:
        vertex_id = vertex_id.replace("%20", " ")
        result = update_vertex(vertex_id, {
            "entity_name": vertex.entity_name,
            "entity_type": vertex.entity_type,
            "description": vertex.description,
            "additional_properties": vertex.additional_properties
        }, vertex.database)
        return {"success": True, "message": "Vertex updated successfully", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.put("/db/hyperedges/{hyperedge_id}")
async def update_hyperedge_endpoint(hyperedge_id: str, hyperedge: HyperedgeUpdateModel):
    """
    Update hyperedge information
    """
    try:
        hyperedge_id = hyperedge_id.replace("%20", " ")
        vertices = hyperedge_id.split("|*|")
        result = update_hyperedge(vertices, {
            "keywords": hyperedge.keywords,
            "summary": hyperedge.summary
        }, hyperedge.database)
        return {"success": True, "message": "Hyperedge updated successfully", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.delete("/db/vertices/{vertex_id}")
async def delete_vertex_endpoint(vertex_id: str, database: str = None):
    """
    Delete vertex
    """
    try:
        vertex_id = vertex_id.replace("%20", " ")
        result = delete_vertex(vertex_id, database)
        return {"success": True, "message": "Vertex deleted successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.delete("/db/hyperedges/{hyperedge_id}")
async def delete_hyperedge_endpoint(hyperedge_id: str, database: str = None):
    """
    Delete hyperedge
    """
    try:
        hyperedge_id = hyperedge_id.replace("%20", " ")
        vertices = hyperedge_id.split("|*|")
        result = delete_hyperedge(vertices, database)
        return {"success": True, "message": "Hyperedge deleted successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# Settings related API endpoints

class SettingsModel(BaseModel):
    apiKey: Optional[str] = None
    clearApiKey: Optional[bool] = False
    modelProvider: Optional[str] = "openrouter"
    modelName: Optional[str] = "nvidia/nemotron-3-ultra-550b-a55b:free"
    baseUrl: Optional[str] = "https://openrouter.ai/api/v1"
    
    embeddingApiKey: Optional[str] = None
    clearEmbeddingApiKey: Optional[bool] = False
    embeddingProvider: Optional[str] = "mistral"
    embeddingModel: Optional[str] = "mistral-embed"
    embeddingBaseUrl: Optional[str] = "https://api.mistral.ai/v1"
    embeddingDim: Optional[int] = 1024
    
    selectedDatabase: Optional[str] = "mock"
    maxTokens: Optional[int] = 2000
    temperature: Optional[float] = 0.7

class APITestModel(BaseModel):
    apiKey: Optional[str] = ""
    baseUrl: Optional[str] = ""
    modelName: Optional[str] = ""
    modelProvider: Optional[str] = "openrouter"
    testType: Optional[str] = "llm"  # "llm" or "embedding"
    embeddingDim: Optional[int] = 1024

class DatabaseTestModel(BaseModel):
    database: str

@app.get("/settings")
async def get_settings():
    """
    Get system settings.
    Full secret keys are NEVER returned in settings responses.
    Returns masked previews and configured flags.
    """
    try:
        settings = get_effective_settings()
        api_key = settings.get("apiKey", "")
        emb_api_key = settings.get("embeddingApiKey", "")
        
        safe_response = {
            "modelProvider": settings.get("modelProvider", "openrouter"),
            "modelName": settings.get("modelName", "nvidia/nemotron-3-ultra-550b-a55b:free"),
            "baseUrl": settings.get("baseUrl", "https://openrouter.ai/api/v1"),
            "apiKey": mask_key(api_key),
            "apiKeyConfigured": bool(api_key.strip() if isinstance(api_key, str) else api_key),
            "apiKeyPreview": mask_key(api_key),
            "openrouter_configured": bool(api_key.strip() if isinstance(api_key, str) else api_key),
            "openrouter_key_preview": mask_key(api_key),
            
            "embeddingProvider": settings.get("embeddingProvider", "mistral"),
            "embeddingModel": settings.get("embeddingModel", "mistral-embed"),
            "embeddingBaseUrl": settings.get("embeddingBaseUrl", "https://api.mistral.ai/v1"),
            "embeddingApiKey": mask_key(emb_api_key),
            "embeddingApiKeyConfigured": bool(emb_api_key.strip() if isinstance(emb_api_key, str) else emb_api_key),
            "embeddingApiKeyPreview": mask_key(emb_api_key),
            "mistral_configured": bool(emb_api_key.strip() if isinstance(emb_api_key, str) else emb_api_key),
            "mistral_key_preview": mask_key(emb_api_key),
            "embeddingDim": settings.get("embeddingDim", 1024),
            
            "selectedDatabase": settings.get("selectedDatabase", "mock"),
            "maxTokens": settings.get("maxTokens", 2000),
            "temperature": settings.get("temperature", 0.7),
        }
        return safe_response
    except Exception as e:
        return {"success": False, "message": sanitize_error_message(str(e))}

@app.post("/settings")
async def save_settings(settings: SettingsModel):
    """
    Save system settings securely.
    WebUI Settings is the single runtime source of truth.
    Credentials survive restart and are kept out of frontend bundles and GET responses.
    """
    try:
        raw_existing = load_raw_settings()
        updated = raw_existing.copy()

        # Handle apiKey (LLM Provider Key)
        if settings.clearApiKey or settings.apiKey == "__CLEAR__":
            updated["apiKey"] = ""
        elif settings.apiKey is not None:
            new_key = settings.apiKey.strip()
            # If masked placeholder sent, preserve existing
            if new_key.startswith("••") or new_key == "***" or new_key == mask_key(raw_existing.get("apiKey", "")):
                pass
            elif new_key:
                updated["apiKey"] = new_key

        # Handle embeddingApiKey (Embedding Provider Key)
        if settings.clearEmbeddingApiKey or settings.embeddingApiKey == "__CLEAR__":
            updated["embeddingApiKey"] = ""
        elif settings.embeddingApiKey is not None:
            new_emb_key = settings.embeddingApiKey.strip()
            # If masked placeholder sent, preserve existing
            if new_emb_key.startswith("••") or new_emb_key == "***" or new_emb_key == mask_key(raw_existing.get("embeddingApiKey", "")):
                pass
            elif new_emb_key:
                updated["embeddingApiKey"] = new_emb_key

        # Update other fields
        if settings.modelProvider:
            updated["modelProvider"] = settings.modelProvider
        if settings.modelName:
            updated["modelName"] = settings.modelName
        if settings.baseUrl:
            updated["baseUrl"] = settings.baseUrl
        if settings.embeddingProvider:
            updated["embeddingProvider"] = settings.embeddingProvider
        if settings.embeddingModel:
            updated["embeddingModel"] = settings.embeddingModel
        if settings.embeddingBaseUrl:
            updated["embeddingBaseUrl"] = settings.embeddingBaseUrl
        if settings.embeddingDim:
            if updated.get("embeddingModel") == "mistral-embed" and settings.embeddingDim != 1024:
                raise ValueError("Mistral embeddings require 1024 dimensions.")
            updated["embeddingDim"] = settings.embeddingDim
        if settings.selectedDatabase is not None:
            updated["selectedDatabase"] = settings.selectedDatabase
        if settings.maxTokens is not None:
            updated["maxTokens"] = settings.maxTokens
        if settings.temperature is not None:
            updated["temperature"] = settings.temperature

        # Persist securely
        os.makedirs(os.path.dirname(os.path.abspath(SETTINGS_FILE)), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(updated, f, ensure_ascii=False, indent=2)
        try:
            if hasattr(os, "chmod"):
                os.chmod(SETTINGS_FILE, 0o600)
        except Exception:
            pass

        # Invalidate cached hyperrag instances so new settings take effect immediately
        hyperrag_instances.clear()

        return {
            "success": True,
            "message": "Settings saved successfully",
            "apiKeyConfigured": bool(updated.get("apiKey")),
            "apiKeyPreview": mask_key(updated.get("apiKey")),
            "embeddingApiKeyConfigured": bool(updated.get("embeddingApiKey")),
            "embeddingApiKeyPreview": mask_key(updated.get("embeddingApiKey")),
        }
    except Exception as e:
        return {"success": False, "message": sanitize_error_message(str(e))}

@app.get("/databases")
async def get_databases():
    """
    Get list of available databases
    """
    try:
        databases = []
        
        # Use db_manager to get databases list
        database_files = db_manager.list_databases()
        
        for file in database_files:
            # Infer description from file name
            description = f"{file.replace('.hgdb', '')} hypergraph"
            
            databases.append({
                "name": file,
                "description": description
            })
        
        # If no database files found, return default list
        if not databases:
            databases = []
        
        return databases
    except Exception as e:
        return {"success": False, "message": str(e), "data": []}

@app.post("/test-api")
async def test_api_connection(api_test: APITestModel):
    """
    Test API connection for LLM or Embedding provider.
    Never exposes API keys or Authorization headers in response or logs.
    """
    try:
        from openai import OpenAI
        raw_settings = load_raw_settings()
        
        is_embedding = (
            api_test.testType == "embedding" or 
            api_test.modelProvider in ("mistral", "embedding")
        )
        
        if is_embedding:
            # Embedding test (Mistral)
            key_to_use = api_test.apiKey.strip() if api_test.apiKey else ""
            if not key_to_use or key_to_use.startswith("••") or key_to_use == "***":
                key_to_use = raw_settings.get("embeddingApiKey", "").strip()
            
            if not key_to_use:
                return {
                    "success": False,
                    "message": "Mistral API key is not configured. Open Settings to add your API key."
                }
            
            base_url = api_test.baseUrl or raw_settings.get("embeddingBaseUrl") or "https://api.mistral.ai/v1"
            model_name = api_test.modelName or raw_settings.get("embeddingModel") or "mistral-embed"
            
            client = OpenAI(api_key=key_to_use, base_url=base_url)
            res = client.embeddings.create(
                model=model_name,
                input=["test connection"],
            )
            dim = len(res.data[0].embedding) if res.data else 0
            return {
                "success": True,
                "message": f"Connection successful! Mistral embedding returned {dim}-dim vector."
            }
        else:
            # LLM test (OpenRouter / OpenAI)
            key_to_use = api_test.apiKey.strip() if api_test.apiKey else ""
            if not key_to_use or key_to_use.startswith("••") or key_to_use == "***":
                key_to_use = raw_settings.get("apiKey", "").strip()
            
            if not key_to_use:
                return {
                    "success": False,
                    "message": "OpenRouter API key is not configured. Open Settings to add your API key."
                }
            
            base_url = api_test.baseUrl or raw_settings.get("baseUrl") or "https://openrouter.ai/api/v1"
            model_name = api_test.modelName or raw_settings.get("modelName") or "nvidia/nemotron-3-ultra-550b-a55b:free"
            
            client = OpenAI(api_key=key_to_use, base_url=base_url)
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return {
                "success": True,
                "message": f"Connection successful! LLM responded (model: {model_name})."
            }
    except Exception as e:
        err_clean = sanitize_error_message(str(e))
        return {"success": False, "message": f"Connection failed: {err_clean}"}

@app.post("/test-database")
async def test_database_connection(db_test: DatabaseTestModel):
    """
    Test database connection
    """
    try:
        # Test database connection using db_manager
        db = db_manager.get_database(db_test.database)
        
        # Attempt to get database basic info to verify connection
        vertices_count = len(db.all_v)
        edges_count = len(db.all_e)
        
        return {
            "success": True, 
            "message": "Database connection test successful",
            "info": {
                "vertices_count": vertices_count,
                "edges_count": edges_count,
                "database": db_test.database
            }
        }
        
    except Exception as e:
        return {"success": False, "message": f"Database connection test failed: {str(e)}"}


# Global HyperRAG instances - dictionary to support multiple databases
hyperrag_instances = {}
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_root_cache = os.path.join(_repo_root, "hyperrag_cache")
hyperrag_working_dir = _root_cache if os.path.exists(_root_cache) else "hyperrag_cache"

def get_effective_settings() -> dict:
    """
    Runtime source of truth for WebUI settings.
    Precedence: WebUI Settings (settings.json) > .env bootstrap > defaults.
    Credentials can be bootstrapped from .env and overridden via WebUI Settings.
    """
    env_openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if not env_openrouter_key and os.getenv("OPENROUTER_API_KEYS"):
        keys = [k.strip() for k in os.getenv("OPENROUTER_API_KEYS", "").split(",") if k.strip()]
        if keys:
            env_openrouter_key = keys[0]

    env_emb_key = os.getenv("EMB_API_KEY", "") or os.getenv("MISTRAL_API_KEY", "")
    if not env_emb_key and os.getenv("EMB_API_KEYS"):
        keys = [k.strip() for k in os.getenv("EMB_API_KEYS", "").split(",") if k.strip()]
        if keys:
            env_emb_key = keys[0]

    base_settings = {
        "modelProvider": os.getenv("OPENROUTER_PROVIDER", "openrouter"),
        "modelName": os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
        "baseUrl": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "apiKey": env_openrouter_key,
        "embeddingProvider": "mistral",
        "embeddingModel": os.getenv("EMB_MODEL", "mistral-embed"),
        "embeddingBaseUrl": os.getenv("EMB_BASE_URL", "https://api.mistral.ai/v1"),
        "embeddingApiKey": env_emb_key,
        "embeddingDim": int(os.getenv("EMB_DIM", "1024")),
        "selectedDatabase": os.getenv("DEFAULT_DATABASE", "mock"),
        "maxTokens": int(os.getenv("MAX_TOKENS", "2000")),
        "temperature": float(os.getenv("TEMPERATURE", "0.7")),
    }

    saved = load_raw_settings()
    if saved:
        # Enforce canonical Mistral embeddings if legacy text-embedding-3-small or missing
        if saved.get("embeddingModel") in ("text-embedding-3-small", None) or saved.get("embeddingDim") in (1536, None):
            saved["embeddingModel"] = "mistral-embed"
            saved["embeddingDim"] = 1024
            saved["embeddingBaseUrl"] = "https://api.mistral.ai/v1"
        base_settings.update(saved)

    return base_settings

async def get_hyperrag_llm_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
    """
    HyperRAG specialized LLM function (async version)
    """
    try:
        main_logger.info(f"Starting LLM call, prompt length: {len(prompt)} chars")
        if system_prompt:
            main_logger.info(f"System prompt length: {len(system_prompt)} chars")
        
        settings = get_effective_settings()
        api_key = settings.get("apiKey", "").strip()
        if not api_key:
            raise ValueError("OpenRouter API key is not configured. Open Settings to add your API key.")
        
        model_name = settings.get("modelName", "nvidia/nemotron-3-ultra-550b-a55b:free")
        base_url = settings.get("baseUrl", "https://openrouter.ai/api/v1")
        
        main_logger.info(f"Using model: {model_name}, API base: {base_url}")
        
        response = await openai_complete_if_cache(
            model_name,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
        
        main_logger.info(f"LLM call complete, response length: {len(response)} chars")
        return response
        
    except Exception as e:
        main_logger.error(f"LLM call failed: {sanitize_error_message(str(e))}")
        raise

async def get_hyperrag_llm_stream_func(prompt, system_prompt=None, history_messages=[], **kwargs):
    """
    HyperRAG specialized streaming LLM function
    """
    try:
        from hyperrag.llm import openrouter_mistral_stream_if_cache
        settings = get_effective_settings()
        api_key = settings.get("apiKey", "").strip()
        if not api_key:
            raise ValueError("OpenRouter API key is not configured. Open Settings to add your API key.")
        
        model_name = settings.get("modelName", "nvidia/nemotron-3-ultra-550b-a55b:free")
        base_url = settings.get("baseUrl", "https://openrouter.ai/api/v1")
        
        async for tok in openrouter_mistral_stream_if_cache(
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        ):
            yield tok
    except Exception as e:
        clean_err = sanitize_error_message(str(e))
        main_logger.error(f"LLM streaming failed: {clean_err}")
        yield f"[STREAM_ERROR: {clean_err}]"

async def get_hyperrag_embedding_func(texts: list[str]) -> np.ndarray:
    """
    HyperRAG specialized embedding function
    """
    try:
        main_logger.info(f"Starting text embedding for {len(texts)} chunks")
        main_logger.info(f"Total chunk length: {sum(len(text) for text in texts)} chars")
        
        settings = get_effective_settings()
        api_key = settings.get("embeddingApiKey", "").strip()
        if not api_key:
            raise ValueError("Mistral API key is not configured. Open Settings to add your API key.")
        
        embedding_model = settings.get("embeddingModel") or "mistral-embed"
        embedding_dim = settings.get("embeddingDim", 1024)
        base_url = settings.get("embeddingBaseUrl") or "https://api.mistral.ai/v1"
        
        main_logger.info(f"Using embedding model: {embedding_model}, dim: {embedding_dim}")
        
        embeddings = await openai_embedding(
            texts,
            model=embedding_model,
            api_key=api_key,
            base_url=base_url,
        )
        
        main_logger.info(f"Text embedding complete, shape: {embeddings.shape}")
        return embeddings
        
    except Exception as e:
        clean_err = sanitize_error_message(str(e))
        main_logger.error(f"Text embedding failed: {clean_err}")
        raise

def get_or_create_hyperrag(database: str = None):
    """
    Get or create HyperRAG instance for specified database
    """
    global hyperrag_instances
    
    if not HYPERRAG_AVAILABLE:
        main_logger.error("HyperRAG is not available")
        raise RuntimeError("HyperRAG is not available")
    
    # If no database specified, use default database
    if not database:
        database = getattr(db_manager, "default_database", "mock")
        main_logger.info(f"Using default database: {database}")
    
    # Check if instance already exists for this database
    if database not in hyperrag_instances:
        main_logger.info(f"Creating new HyperRAG instance for database: {database}")
        
        # Use database name as working directory (strip .hgdb suffix)
        if database.endswith('.hgdb'):
            db_dir_name = database.replace('.hgdb', '')
        else:
            db_dir_name = database
            
        # HyperRAG working dir uses database folder under hyperrag_cache
        db_working_dir = os.path.join(hyperrag_working_dir, db_dir_name)
        Path(db_working_dir).mkdir(parents=True, exist_ok=True)
        
        main_logger.info(f"HyperRAG working dir: {db_working_dir}")
        settings = get_effective_settings()
            
        embedding_dim = settings.get("embeddingDim", 1024)
        
        # Initialize HyperRAG instance
        hyperrag_instances[database] = HyperRAG(
            working_dir=db_working_dir,
            llm_model_func=get_hyperrag_llm_func,
            llm_model_stream_func=get_hyperrag_llm_stream_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=embedding_dim,
                max_token_size=8192,
                func=get_hyperrag_embedding_func
            ),
        )
        
        main_logger.info(f"HyperRAG instance initialized successfully for database: {database}")
    else:
        main_logger.info(f"Using existing HyperRAG instance for database: {database}")
    
    return hyperrag_instances[database]
    
    return hyperrag_instances[database]


class Message(BaseModel):
    message: str

@app.post("/process_message")
async def process_message(msg: Message):
    user_message = msg.message
    try:
        response_message = await get_hyperrag_llm_func(prompt=user_message)
    except Exception as e:
        return {"response": str(e)} 
    return {"response": response_message}

# HyperRAG QA related endpoints

class DocumentModel(BaseModel):
    content: str
    retries: int = 3
    database: str = None  # Database parameter

class QueryModel(BaseModel):
    question: str
    mode: str = "adaptive"  # adaptive, hyper, hyper-lite, naive
    top_k: int = 60
    max_token_for_text_unit: int = 1600
    max_token_for_entity_context: int = 300
    max_token_for_relation_context: int = 1600
    only_need_context: bool = False
    response_type: str = "Multiple Paragraphs"
    database: str = None  # Database parameter

@app.post("/hyperrag/insert")
async def insert_document(doc: DocumentModel):
    """
    Insert document into specified database HyperRAG instance
    """
    if not HYPERRAG_AVAILABLE:
        return {"success": False, "message": "HyperRAG is not available"}
    
    try:
        rag = get_or_create_hyperrag(doc.database)
        
        # Retry mechanism
        for attempt in range(doc.retries):
            try:
                await rag.ainsert(doc.content)
                return {
                    "success": True, 
                    "message": "Document inserted successfully",
                    "database": doc.database or "default"
                }
            except Exception as e:
                if attempt == doc.retries - 1:
                    raise e
                print(f"Insert attempt {attempt + 1} failed: {e}. Retrying...")
                await asyncio.sleep(2)
                
    except Exception as e:
        return {"success": False, "message": f"Failed to insert document: {str(e)}"}

@app.post("/hyperrag/query")
async def query_hyperrag(query: QueryModel):
    """
    Query HyperRAG for specified database
    """
    if not HYPERRAG_AVAILABLE:
        return {"success": False, "message": "HyperRAG is not available"}
    
    try:
        rag = get_or_create_hyperrag(query.database)
        
        # Create query parameters
        param = QueryParam(
            mode=query.mode,
            top_k=query.top_k,
            max_token_for_text_unit=query.max_token_for_text_unit,
            max_token_for_entity_context=query.max_token_for_entity_context,
            max_token_for_relation_context=query.max_token_for_relation_context,
            only_need_context=query.only_need_context,
            response_type=query.response_type,
            return_type='json'
        )
        
        # Execute query
        result = await rag.aquery(query.question, param)
        
        # Format results
        decision_dict = result.get("adaptive_decision") or (
            rag.last_adaptive_decision.to_dict()
            if getattr(rag, "last_adaptive_decision", None)
            else None
        )
        val_dict = result.get("validation") or (
            rag.last_validation_result.to_dict()
            if getattr(rag, "last_validation_result", None)
            else None
        )
        lang_dict = result.get("language_guard") or (
            rag.last_language_result.to_dict()
            if getattr(rag, "last_language_result", None)
            else None
        )
        return {
            "success": True,
            "response": result.get("response", ""),
            "answer": result.get("response", ""),
            "entities": result.get("entities", []),
            "hyperedges": result.get("hyperedges", []),
            "text_units": result.get("text_units", []),
            "mode": query.mode,
            "question": query.question,
            "database": query.database or "default",
            "adaptive_decision": decision_dict,
            "validation": val_dict,
            "language_guard": lang_dict,
        }
        
    except Exception as e:
        err_msg = str(e)
        sanitized = sanitize_error_message(err_msg)
        if "API key is not configured" in err_msg:
            return {"success": False, "message": sanitized}
        return {"success": False, "message": f"Query failed: {sanitized}"}

@app.post("/hyperrag/query_stream")
async def query_hyperrag_stream(query: QueryModel):
    """
    Stream HyperRAG query token-by-token.
    """
    if not HYPERRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="HyperRAG is not available")

    try:
        rag = get_or_create_hyperrag(query.database)
        param = QueryParam(
            mode=query.mode,
            top_k=query.top_k,
            max_token_for_text_unit=query.max_token_for_text_unit,
            max_token_for_entity_context=query.max_token_for_entity_context,
            max_token_for_relation_context=query.max_token_for_relation_context,
            only_need_context=query.only_need_context,
            response_type=query.response_type,
        )

        from fastapi.responses import StreamingResponse

        async def stream_generator():
            try:
                async for token in rag.astream_query(query.question, param):
                    if token:
                        yield token
                    await asyncio.sleep(0)
            except Exception as stream_err:
                clean_err = sanitize_error_message(str(stream_err))
                yield f"\n[STREAM_ERROR: {clean_err}]"

        return StreamingResponse(stream_generator(), media_type="text/plain; charset=utf-8")
    except Exception as e:
        clean_err = sanitize_error_message(str(e))
        status_code = 400 if "API key is not configured" in str(e) else 500
        raise HTTPException(status_code=status_code, detail=f"Query stream failed: {clean_err}")

@app.get("/hyperrag/status")
async def get_hyperrag_status(database: str = None):
    """
    Get status of HyperRAG instance for specified database
    """
    try:
        status = {
            "available": HYPERRAG_AVAILABLE,
            "database": database or "default",
            "working_dir": hyperrag_working_dir,
            "instances": list(hyperrag_instances.keys())
        }
        
        if database:
            # Get status for specific database
            if database in hyperrag_instances:
                instance = hyperrag_instances[database]
                status["initialized"] = True
                try:
                    status["details"] = {
                        "chunk_token_size": instance.chunk_token_size,
                        "llm_model_name": instance.llm_model_name,
                        "embedding_func_available": instance.embedding_func is not None,
                        "working_dir": os.path.join(hyperrag_working_dir, database.replace('.hgdb', ''))
                    }
                except Exception as e:
                    status["details"] = f"Error getting details: {str(e)}"
            else:
                status["initialized"] = False
        else:
            # Get overview of all instances
            status["initialized"] = len(hyperrag_instances) > 0
            status["total_instances"] = len(hyperrag_instances)
        
        return status
        
    except Exception as e:
        return {"success": False, "message": f"Failed to get status: {str(e)}"}

@app.delete("/hyperrag/reset")
async def reset_hyperrag(database: str = None):
    """
    Reset HyperRAG instance for specified database, or all instances
    """
    global hyperrag_instances
    
    try:
        if database:
            # Reset instance for specific database
            if database in hyperrag_instances:
                del hyperrag_instances[database]
                return {
                    "success": True, 
                    "message": f"HyperRAG instance for database '{database}' reset successfully"
                }
            else:
                return {
                    "success": False, 
                    "message": f"No HyperRAG instance found for database '{database}'"
                }
        else:
            # Reset all instances
            hyperrag_instances = {}
            return {"success": True, "message": "All HyperRAG instances reset successfully"}
            
    except Exception as e:
        return {"success": False, "message": f"Failed to reset: {str(e)}"}

# File management API endpoints

class FileEmbedRequest(BaseModel):
    file_ids: List[str]
    chunk_size: int = 1000
    chunk_overlap: int = 200

@app.get("/files")
async def get_files():
    """
    Get list of all uploaded files
    """
    try:
        files = file_manager.get_all_files()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file list: {str(e)}")

@app.post("/files/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload files endpoint
    """
    print(f"\n{'='*50}")
    print(f"[INFO] Starting file upload, file count: {len(files)}")
    print(f"{'='*50}")
    
    results = []
    
    for i, file in enumerate(files):
        try:
            print(f"\n[INFO] Uploading file {i+1}/{len(files)}: {file.filename}")
            print(f"[INFO] File size: {file.size if hasattr(file, 'size') else 'unknown'} bytes")
            
            # Read file content
            print("[INFO] Reading file content...")
            content = await file.read()
            print(f"[OK] File content read complete, size: {len(content)} bytes")
            
            # Save file
            print("[INFO] Saving file locally...")
            file_info = await file_manager.save_uploaded_file(content, file.filename)
            file_info["status"] = "uploaded"
            print(f"[OK] File saved successfully: {file_info['filename']}")
            print(f"  - File ID: {file_info['file_id']}")
            print(f"  - Storage path: {file_info['file_path']}")
            print(f"  - Database: {file_info['database_name']}")
            
            results.append(file_info)
            
        except Exception as e:
            error_msg = f"File upload failed: {file.filename}, error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            main_logger.error(error_msg)
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
    
    print(f"\n[OK] File upload completed, successful: {len([r for r in results if r.get('status') == 'uploaded'])}/{len(files)}")
    print(f"{'='*50}")
    
    return {"files": results}

@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """
    Delete specified file
    """
    try:
        success = file_manager.delete_file(file_id)
        if success:
            return {"success": True, "message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File does not exist")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@app.post("/files/embed")
async def embed_files(request: FileEmbedRequest):
    """
    Batch embed documents into HyperRAG
    """
    if not HYPERRAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="HyperRAG is not available")
    
    print(f"\n{'='*50}")
    print(f"[INFO] Starting document embedding, file count: {len(request.file_ids)}")
    print(f"[INFO] Config parameters: chunk_size={request.chunk_size}, chunk_overlap={request.chunk_overlap}")
    print(f"{'='*50}")
    
    results = []
    
    try:
        for i, file_id in enumerate(request.file_ids):
            try:
                print(f"\n[INFO] Processing file {i+1}/{len(request.file_ids)}: {file_id}")
                
                # Update file status to processing
                print("[INFO] Updating file status to processing...")
                file_manager.update_file_status(file_id, "processing")
                
                # Get file info
                print("[INFO] Getting file info...")
                file_info = file_manager.get_file_by_id(file_id)
                if not file_info:
                    error_msg = f"File does not exist: {file_id}"
                    print(f"[ERROR] {error_msg}")
                    results.append({
                        "file_id": file_id,
                        "status": "error",
                        "error": "File does not exist"
                    })
                    continue
                
                print(f"[OK] File info: {file_info['filename']} ({file_info['file_size']} bytes)")
                
                # Use database name corresponding to file
                database_name = file_info["database_name"]
                print(f"[INFO] Target database: {database_name}")
                
                if GENERIC_INGESTION_AVAILABLE:
                    pipeline = GenericIngestionPipeline(
                        IngestionConfig(
                            max_records=50,
                            chunk_token_size=request.chunk_size,
                            chunk_overlap_token_size=request.chunk_overlap,
                            llm_func=get_hyperrag_llm_func,
                            embedding_func=get_hyperrag_embedding_func,
                        )
                    )
                    await pipeline.ingest_file(
                        file_info["file_path"],
                        target_database_name=database_name,
                        original_filename=file_info["filename"],
                    )
                else:
                    rag = get_or_create_hyperrag(database_name)
                    content = await file_manager.read_file_content(file_info["file_path"])
                    await rag.ainsert(content)
                
                print("[OK] Document embedding complete")
                
                # Update file status to embedded
                file_manager.update_file_status(file_id, "embedded")
                
                results.append({
                    "file_id": file_id,
                    "filename": file_info["filename"],
                    "database_name": database_name,
                    "status": "embedded"
                })
                
                print(f"[OK] File {file_info['filename']} embedded successfully")
                
            except Exception as e:
                # Update file status to error
                error_msg = f"File embedding failed: {file_id}, error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                file_manager.update_file_status(file_id, "error", str(e))
                
                results.append({
                    "file_id": file_id,
                    "status": "error",
                    "error": str(e)
                })
        
        successful = len([r for r in results if r.get('status') == 'embedded'])
        print(f"\n[OK] Document embedding complete, successful: {successful}/{len(request.file_ids)}")
        print(f"{'='*50}")
        
        return {"embedded_files": results}
        
    except Exception as e:
        error_msg = f"Batch embedding failed: {str(e)}"
        print(f"[ERROR] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

# Custom log handler sending logs over WebSocket
class WebSocketLogHandler(logging.Handler):
    def __init__(self, connection_manager):
        super().__init__()
        self.connection_manager = connection_manager
        
    def emit(self, record):
        try:
            log_message = self.format(record)
            # Send log message asynchronously
            asyncio.create_task(self.connection_manager.send_log_message({
                "type": "log",
                "level": record.levelname,
                "message": log_message,
                "timestamp": record.created,
                "logger_name": record.name
            }))
        except Exception:
            pass  # Avoid log handler errors affecting main program

# Custom stream handler capturing stdout/stderr
class WebSocketStreamHandler:
    def __init__(self, connection_manager, stream_type="stdout"):
        self.connection_manager = connection_manager
        self.stream_type = stream_type
        self.original_stream = sys.stdout if stream_type == "stdout" else sys.stderr
        
    def write(self, message):
        # Also write to original stream
        self.original_stream.write(message)
        self.original_stream.flush()
        
        # Send to WebSocket (strip empty lines)
        if message.strip():
            asyncio.create_task(self.connection_manager.send_log_message({
                "type": "console",
                "level": "ERROR" if self.stream_type == "stderr" else "INFO",
                "message": message.strip(),
                "timestamp": asyncio.get_event_loop().time(),
                "source": self.stream_type
            }))
    
    def flush(self):
        self.original_stream.flush()

# WebSocket connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logging_enabled = False
        self.original_stdout = None
        self.original_stderr = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # If first connection, enable logging redirect
        if len(self.active_connections) == 1 and not self.logging_enabled:
            self.enable_logging_redirect()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # If no connections remain, disable logging redirect
        if len(self.active_connections) == 0 and self.logging_enabled:
            self.disable_logging_redirect()

    def enable_logging_redirect(self):
        """Enable logging redirect."""
        if not self.logging_enabled:
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            
            # Redirect stdout and stderr
            sys.stdout = WebSocketStreamHandler(self, "stdout")
            sys.stderr = WebSocketStreamHandler(self, "stderr")
            
            self.logging_enabled = True
            print("[INFO] Logging redirect enabled")

    def disable_logging_redirect(self):
        """Disable logging redirect."""
        if self.logging_enabled and self.original_stdout and self.original_stderr:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self.logging_enabled = False
            print("[INFO] Logging redirect disabled")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # If disconnected, mark for removal
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def send_progress_update(self, progress_data: dict):
        """Send progress update to all connected clients."""
        message = json.dumps(progress_data)
        await self.broadcast(message)
    
    async def send_log_message(self, log_data: dict):
        """Send log message to all connected clients."""
        message = json.dumps(log_data)
        await self.broadcast(message)

manager = ConnectionManager()

# Set up comprehensive logging configuration
def setup_comprehensive_logging():
    """Set up comprehensive logging configuration."""
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create WebSocket handler
    ws_handler = WebSocketLogHandler(manager)
    ws_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ws_handler.setFormatter(formatter)
    
    # Create console handler (preserve console output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(ws_handler)
    root_logger.addHandler(console_handler)
    
    # Set log level for specific modules
    logging.getLogger('hyperrag').setLevel(logging.INFO)
    logging.getLogger('openai').setLevel(logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)  # Reduce HTTP request logs
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Ensure all HyperRAG submodules emit logs
    hyperrag_modules = [
        'hyperrag.base',
        'hyperrag.hyperrag', 
        'hyperrag.llm',
        'hyperrag.operate',
        'hyperrag.prompt',
        'hyperrag.storage',
        'hyperrag.utils'
    ]
    
    for module_name in hyperrag_modules:
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(logging.INFO)
        # Ensure module logs propagate to root logger
        module_logger.propagate = True
    
    return root_logger

def configure_hyperrag_logging():
    """Configure HyperRAG detailed logging output."""
    try:
        # If HyperRAG available, configure internal logging
        if HYPERRAG_AVAILABLE:
            # Import HyperRAG modules and configure loggers
            try:
                import hyperrag
                import hyperrag.base
                import hyperrag.storage
                import hyperrag.llm
                import hyperrag.utils
                
                # Configure loggers for primary HyperRAG modules
                modules_to_configure = [
                    hyperrag,
                    hyperrag.base,
                    hyperrag.storage, 
                    hyperrag.llm,
                    hyperrag.utils
                ]
                
                for module in modules_to_configure:
                    if hasattr(module, '__name__'):
                        logger = logging.getLogger(module.__name__)
                        logger.setLevel(logging.INFO)
                        logger.propagate = True
                        
                print("[INFO] HyperRAG logging configured successfully")
                        
            except ImportError as e:
                print(f"[WARN] Failed to import HyperRAG modules for logging configuration: {e}")
                
    except Exception as e:
        print(f"[WARN] HyperRAG logging configuration failed: {e}")

# Initialize logging system
main_logger = setup_comprehensive_logging()

# Configure HyperRAG logging
configure_hyperrag_logging()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client-sent messages here
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Document embedding endpoint with real-time progress
@app.post("/files/embed-with-progress")
async def embed_files_with_progress(request: FileEmbedRequest):
    """
    Batch embed documents into HyperRAG with real-time progress notification
    """
    if not HYPERRAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="HyperRAG is not available")
    
    # Return initial response immediately
    total_files = len(request.file_ids)
    
    # Process document embedding asynchronously
    asyncio.create_task(process_files_with_progress(request, total_files))
    
    return {
        "message": "Document embedding processing started",
        "total_files": total_files,
        "processing": True
    }

async def process_files_with_progress(request: FileEmbedRequest, total_files: int):
    """Asynchronously process file embedding and emit progress updates."""
    try:
        print(f"="*60)
        print(f"[INFO] Starting batch document embedding task")
        print(f"[INFO] Total files: {total_files}")
        print(f"[INFO] Config parameters: chunk_size={request.chunk_size}, chunk_overlap={request.chunk_overlap}")
        print(f"="*60)
        
        main_logger.info(f"Starting batch embedding for {total_files} files")
        main_logger.info(f"Config parameters: chunk_size={request.chunk_size}, chunk_overlap={request.chunk_overlap}")
        
        successful_files = 0
        failed_files = 0
        
        for i, file_id in enumerate(request.file_ids):
            try:
                print(f"\n{'='*40}")
                print(f"[INFO] Processing file {i + 1}/{total_files}")
                print(f"[INFO] File ID: {file_id}")
                print(f"{'='*40}")
                
                # Send progress update
                await manager.send_progress_update({
                    "type": "progress",
                    "file_id": file_id,
                    "current": i + 1,
                    "total": total_files,
                    "percentage": ((i + 1) / total_files) * 100,
                    "status": "processing",
                    "message": f"Processing file {i + 1}/{total_files}"
                })
                
                # Update file status to processing
                print("[INFO] Updating file status to processing...")
                file_manager.update_file_status(file_id, "processing")
                
                # Get file info
                print("[INFO] Getting file info...")
                main_logger.info(f"Getting file info: {file_id}")
                file_info = file_manager.get_file_by_id(file_id)
                if not file_info:
                    error_msg = f"File does not exist: {file_id}"
                    print(f"[ERROR] {error_msg}")
                    main_logger.error(error_msg)
                    await manager.send_progress_update({
                        "type": "error",
                        "file_id": file_id,
                        "error": "File does not exist",
                        "current": i + 1,
                        "total": total_files
                    })
                    failed_files += 1
                    continue
                
                print(f"[OK] File info retrieved successfully:")
                print(f"  - Filename: {file_info['filename']}")
                print(f"  - File size: {file_info['file_size']} bytes")
                print(f"  - Upload time: {file_info['upload_time']}")
                
                # Use database name corresponding to file
                database_name = file_info["database_name"]
                print(f"  - Target database: {database_name}")
                
                main_logger.info(f"Processing file: {file_info['filename']} ({file_info['file_size']} bytes), database: {database_name}")
                
                if GENERIC_INGESTION_AVAILABLE:
                    async def progress_cb(stage: str, details: dict):
                        await manager.send_progress_update({
                            "type": "file_processing",
                            "file_id": file_id,
                            "filename": file_info["filename"],
                            "database_name": database_name,
                            "stage": stage,
                            "message": details.get("message", f"Stage: {stage}")
                        })

                    pipeline = GenericIngestionPipeline(
                        IngestionConfig(
                            max_records=50,
                            chunk_token_size=request.chunk_size,
                            chunk_overlap_token_size=request.chunk_overlap,
                            llm_func=get_hyperrag_llm_func,
                            embedding_func=get_hyperrag_embedding_func,
                        )
                    )
                    await pipeline.ingest_file(
                        file_info["file_path"],
                        target_database_name=database_name,
                        original_filename=file_info["filename"],
                        progress_callback=progress_cb
                    )
                else:
                    print("[INFO] Initializing HyperRAG instance...")
                    main_logger.info(f"Initializing HyperRAG instance, database: {database_name}")
                    rag = get_or_create_hyperrag(database_name)
                    print("[OK] HyperRAG instance initialized successfully")
                    
                    content = await file_manager.read_file_content(file_info["file_path"])
                    await rag.ainsert(content)
                
                print("[OK] Document embedding complete!")
                main_logger.info(f"Document embedding complete: {file_info['filename']}, database: {database_name}")
                
                # Update file status to embedded
                file_manager.update_file_status(file_id, "embedded")
                
                # Send success progress update
                await manager.send_progress_update({
                    "type": "file_completed",
                    "file_id": file_id,
                    "filename": file_info["filename"],
                    "database_name": database_name,
                    "status": "completed",
                    "message": f"Document embedding complete: {file_info['filename']} (database: {database_name})"
                })
                
                successful_files += 1
                print(f"[OK] File {file_info['filename']} processed successfully!")
                
            except Exception as e:
                # Update file status to error
                error_msg = f"File processing failed: {file_id}, error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                main_logger.error(error_msg)
                file_manager.update_file_status(file_id, "error", str(e))
                
                # Send error progress update
                await manager.send_progress_update({
                    "type": "file_error",
                    "file_id": file_id,
                    "error": str(e),
                    "current": i + 1,
                    "total": total_files
                })
                
                failed_files += 1
        
        # Send overall completion progress update
        print(f"\n{'='*60}")
        print("[SUCCESS] Batch document processing complete!")
        print(f"Total files: {total_files}")
        print(f"Successfully processed: {successful_files}")
        print(f"Failed: {failed_files}")
        print(f"Success rate: {(successful_files/total_files)*100:.1f}%")
        print(f"{'='*60}")
        
        main_logger.info(f"All documents processed! Total: {total_files}, success: {successful_files}, failed: {failed_files}")
        await manager.send_progress_update({
            "type": "all_completed",
            "message": f"All documents processed (success: {successful_files}, failed: {failed_files})",
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files
        })
        
    except Exception as e:
        # Send overall error message
        error_msg = f"Batch embedding failed: {str(e)}"
        print(f"[ERROR] {error_msg}")
        main_logger.error(error_msg)
        await manager.send_progress_update({
            "type": "error",
            "error": error_msg
        })

@app.post("/ingestion/preflight")
async def ingestion_preflight(
    file: Optional[UploadFile] = File(None),
    file_id: Optional[str] = Form(None)
):
    """
    Preflight inspection of an uploaded file or existing file_id.
    Zero external API calls.
    """
    if not GENERIC_INGESTION_AVAILABLE:
        raise HTTPException(status_code=500, detail="Generic Ingestion pipeline not available")
    try:
        pipeline = GenericIngestionPipeline()
        if file is not None:
            content = await file.read()
            temp_dir = Path("scratch") / "preflight"
            temp_dir.mkdir(parents=True, exist_ok=True)
            safe_name = Path(file.filename).name
            temp_path = temp_dir / safe_name
            with open(temp_path, "wb") as f:
                f.write(content)
            report = pipeline.preflight_inspect(temp_path, original_filename=file.filename)
            try:
                temp_path.unlink()
            except Exception:
                pass
            return {"success": True, "report": report.to_dict()}
        elif file_id is not None:
            file_info = file_manager.get_file_by_id(file_id)
            if not file_info:
                raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
            report = pipeline.preflight_inspect(file_info["file_path"], original_filename=file_info["filename"])
            return {"success": True, "report": report.to_dict()}
        else:
            raise HTTPException(status_code=400, detail="Either file or file_id must be provided")
    except Exception as e:
        main_logger.error(f"Preflight inspection failed: {e}")
        return {"success": False, "error": str(e)}

@app.post("/ingestion/upload-and-process")
async def upload_and_process(
    file: UploadFile = File(...),
    database_name: Optional[str] = Form(None),
    max_records: int = Form(50)
):
    """
    Generic one-click upload & ingestion pipeline endpoint.
    Uploads raw file, inspects, normalizes, synthesizes contexts,
    and indexes into an isolated Hyper-RAG knowledge base.
    """
    if not GENERIC_INGESTION_AVAILABLE:
        raise HTTPException(status_code=500, detail="Generic Ingestion pipeline not available")
    try:
        content = await file.read()
        file_info = await file_manager.save_uploaded_file(content, file.filename)
        file_id = file_info["file_id"]

        target_db = database_name or file_info["database_name"]
        target_db = sanitize_database_name(target_db)

        # Broadcast start event
        await manager.broadcast(json.dumps({
            "type": "file_processing",
            "file_id": file_id,
            "filename": file.filename,
            "database_name": target_db,
            "stage": "inspecting",
            "message": f"Starting ingestion for {file.filename}"
        }))

        async def ws_cb(stage: str, details: dict):
            await manager.broadcast(json.dumps({
                "type": "file_processing",
                "file_id": file_id,
                "filename": file.filename,
                "database_name": target_db,
                "stage": stage,
                "message": details.get("message", f"Stage: {stage}")
            }))

        pipeline = GenericIngestionPipeline(IngestionConfig(max_records=max_records))
        file_manager.update_file_status(file_id, "processing")

        result = await pipeline.ingest_file(
            file_info["file_path"],
            target_database_name=target_db,
            original_filename=file.filename,
            progress_callback=ws_cb
        )

        file_manager.update_file_status(file_id, "embedded")

        await manager.broadcast(json.dumps({
            "type": "file_completed",
            "file_id": file_id,
            "filename": file.filename,
            "database_name": target_db,
            "status": "completed",
            "message": f"Knowledge base '{target_db}' is ready!"
        }))

        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "database_name": target_db,
            "records_indexed": result.get("records_indexed", 0),
            "contexts_indexed": result.get("contexts_indexed", 0),
            "status": "ready"
        }
    except Exception as e:
        main_logger.error(f"Upload and process failed: {e}", exc_info=True)
        if 'file_id' in locals():
            file_manager.update_file_status(file_id, "error", str(e))
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/{full_path:path}")
async def serve_spa_fallback(full_path: str):
    if full_path.startswith(("db", "hyperrag", "files", "settings", "databases", "docs", "openapi.json", "ws", "test-api", "ingestion", "health")):
        raise HTTPException(status_code=404, detail="Not Found")
    index_file = os.path.join(frontend_dist_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Not Found")

