from fastapi import FastAPI

from app.api.v1.indexer import router as indexer_router

app = FastAPI()

app.include_router(indexer_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "synapse-platform API"}
