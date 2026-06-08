from fastapi import FastAPI
from app.api.routes import router
from app.db.init_db import init_db

app = FastAPI(
    title="Persistent Sales Assistant Agent",
    description="Backend API for a sales assistant with persistent memory, real tools, and self-evaluation.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(router)
