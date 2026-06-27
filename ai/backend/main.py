import sys
from pathlib import Path

_MODEL_DIR = str(Path(__file__).resolve().parent.parent / "model")
if _MODEL_DIR not in sys.path:
    sys.path.insert(0, _MODEL_DIR)

_BACKEND_DIR = str(Path(__file__).resolve().parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health, pkm, projects, validation

app = FastAPI(
    title="AI Proposal Backend",
    description="Backend for PKM Proposal Generator",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(pkm.router, prefix="/api/pkm")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(validation.router, prefix="/api/validation")


@app.get("/")
async def root():
    return {"message": "AI Proposal Backend is running", "docs": "/docs"}


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("CHAT_PORT", "8000")))