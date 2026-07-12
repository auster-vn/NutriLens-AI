import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.rate_limit import enforce_rate_limit
from app.core.schema import initialize_schema
from app.dashboard.router import router as dashboard_router
from app.favorites.router import router as favorites_router
from app.meal.router import router as meal_router
from app.observability.metrics import registry as metrics_registry
from app.pantry.router import router as pantry_router
from app.products.history_router import router as scan_history_router
from app.products.router import router as products_router
from app.profile.router import router as profile_router
from app.rag.router import router as rag_router
from app.schemas.common import HealthResponse


async def initialize_schema_in_background(application: FastAPI) -> None:
    try:
        await initialize_schema(engine, settings.database_url)
    except Exception as exc:  # noqa: BLE001
        application.state.schema_error = exc
        logging.getLogger("nutrilens.schema").exception("Schema initialization failed.")
    else:
        application.state.schema_ready = True


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings.validate_production_secrets()
    application.state.schema_ready = False
    application.state.schema_error = None
    schema_task = asyncio.create_task(initialize_schema_in_background(application))
    application.state.schema_task = schema_task
    try:
        yield
    finally:
        if not schema_task.done():
            schema_task.cancel()
            with suppress(asyncio.CancelledError):
                await schema_task


settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logging.getLogger("nutrilens.validation").info(
        "Request validation failed path=%s request_id=%s fields=%s",
        request.url.path,
        request_id,
        [".".join(map(str, error.get("loc", []))) for error in exc.errors()],
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "error": {"code": "VALIDATION_ERROR", "message": "Request validation failed."},
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logging.getLogger("nutrilens.error").exception(
        "Unhandled request error path=%s request_id=%s",
        request.url.path,
        request_id,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "INTERNAL_ERROR",
                "message": "Hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
            }
        },
        headers={"X-Request-ID": request_id or "unknown"},
    )


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id
    started_at = perf_counter()
    try:
        enforce_rate_limit(request)
    except HTTPException as exc:
        response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    else:
        response = await call_next(request)
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' https: data:; "
        "connect-src 'self' https://world.openfoodfacts.org; frame-ancestors 'none'"
    )
    logging.getLogger("nutrilens.request").info(
        "%s %s %s %.2fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    metrics_registry.observe_http(request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.api_route("/health", methods=["GET", "OPTIONS"], response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)


@app.api_route("/", methods=["GET", "OPTIONS"], response_model=HealthResponse)
async def root_health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)


@app.get("/version")
async def version() -> dict[str, str]:
    return {"version": settings.app_version}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(metrics_registry.render_prometheus(), media_type="text/plain; version=0.0.4")


@app.api_route("/health/ready", methods=["GET", "OPTIONS"], response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse:
    if request.method == "OPTIONS":
        return HealthResponse(status="ok", version=settings.app_version)
    schema_task = getattr(app.state, "schema_task", None)
    if schema_task and not schema_task.done():
        raise HTTPException(status_code=503, detail="Schema initialization is still running.")
    schema_error = getattr(app.state, "schema_error", None)
    if schema_error:
        raise HTTPException(status_code=503, detail="Schema initialization failed.")
    async with engine.connect() as connection:
        await connection.execute(text("select 1"))
    return HealthResponse(status="ready", version=settings.app_version)


app.include_router(products_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(favorites_router)
app.include_router(scan_history_router)
app.include_router(profile_router)
app.include_router(pantry_router)
app.include_router(meal_router)
app.include_router(rag_router)
app.include_router(admin_router)
