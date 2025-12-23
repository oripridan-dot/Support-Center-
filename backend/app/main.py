from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.database import create_db_and_tables
from .api import brands, chat, ingestion
from .scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    start_scheduler()
    yield

app = FastAPI(title="Halilit Support Center API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(brands.router, prefix="/api/brands", tags=["brands"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Halilit Support Center API"}
