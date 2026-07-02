from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes import router

app = FastAPI(
    title="Real Estate AI Opportunity API",
    description="API for scraping, analyzing and notifying real estate opportunities",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"message": "HolanducIA API", "status": "online", "database": "postgres"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
