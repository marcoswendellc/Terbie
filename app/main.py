from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import TerbieError
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings)

app = FastAPI(title=settings.app_name)
web_dir = Path(__file__).resolve().parent / "web"
app.mount("/ui", StaticFiles(directory=web_dir), name="ui")
app.include_router(router)


@app.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(web_dir / "index.html")


@app.exception_handler(TerbieError)
async def terbie_error_handler(
    _request: Request,
    exc: TerbieError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
        },
    )
