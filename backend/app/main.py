from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.indexer import router as indexer_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(indexer_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "synapse-platform API"}
