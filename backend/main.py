from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.llm.providers import provider_status
from backend.rag.ingest import ensure_knowledge_base_ingested
from backend.routers import agents, auth, cases, decisions
from backend.store import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_knowledge_base_ingested()
    yield


app = FastAPI(title="Risk Assessment Workbench API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(agents.router)
app.include_router(decisions.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/llm/providers")
async def llm_providers():
    return provider_status()
