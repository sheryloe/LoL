from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_NAME, APP_VERSION
from app.routers.projects import router as projects_router
from app.routers.ui import router as ui_router
from app.routers.workers import router as workers_router

app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(ui_router)
app.include_router(projects_router)
app.include_router(workers_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(PermissionError)
async def permission_error_handler(_, exc: PermissionError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})
