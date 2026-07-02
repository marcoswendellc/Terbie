from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import TerbieError
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings)

app = FastAPI(title=settings.app_name)
app.include_router(router)


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
