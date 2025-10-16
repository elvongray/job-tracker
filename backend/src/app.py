from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.activities.router import router as activities_router
from src.applications.router import router as applications_router
from src.auth import router as auth_router
from src.core.config import settings
from src.core.error_handler import add_exception_handlers

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_exception_handlers(app)


@app.get("/_health")
def health():
    return {"status": "ok"}


app.include_router(auth_router.router)
app.include_router(applications_router)
app.include_router(activities_router)
