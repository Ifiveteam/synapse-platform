from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.profiler.api import router as profiler_router
from app.agents.profiler.load_env import load_backend_env

load_backend_env()

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(profiler_router)


def create_app() -> FastAPI:
    app = FastAPI(title="Synapse Platform API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
