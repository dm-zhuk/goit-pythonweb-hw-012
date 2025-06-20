from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter

from src.database.connect import init_db, rc
from src.services.base import settings
from src.routers import contacts, users, utils

import uvicorn

app = FastAPI(title="Contacts API", description="Contacts management REST API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.BASE_URL, "http://127.0.0.1:8000", "http://localhost:5500"],
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

if __name__ == "__main__":
    uvicorn.run("src.main:app", debug=True, reload=True)
