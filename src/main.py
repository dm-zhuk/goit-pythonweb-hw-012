from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter

from src.database.db import init_db, rc
from src.routers import contacts, users, utils
from prometheus_fastapi_instrumentator import Instrumentator

import uvicorn


app = FastAPI(title="Contacts API", description="Contacts management REST API")

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """
    Application startup event handler.
    Initializes the database and the FastAPI rate limiter.
    """
    await init_db()
    await FastAPILimiter.init(rc)


app.include_router(utils.router, prefix="/api")
app.include_router(contacts.router, prefix="/api/contacts")
app.include_router(users.router)


"""
docker-compose -f docker-compose.test.yaml up --build -d

Unit only (pure mocks):
poetry run pytest tests/unit
-------------------
docker stop test-db

"""
if __name__ == "__main__":
    uvicorn.run("src.main:app", debug=True, reload=True)
