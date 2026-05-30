from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import projects, health, validation

app = FastAPI(
    title="AI Proposal Backend",
    description="Backend for PKM Proposal Generator",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(validation.router, prefix="/api/validation")


@app.get("/")
async def root():
    return {"message": "AI Proposal Backend is running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)