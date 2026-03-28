from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.deposits import router as deposits_router

app = FastAPI(title="Deposits API")

app.include_router(health_router)
app.include_router(deposits_router)