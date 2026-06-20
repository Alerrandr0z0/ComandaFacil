import re
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.admin.api.routes import router as admin_router
from app.analytics.api.routes import router as analytics_router

# Import routers
from app.auth.api.routes import router as auth_router
from app.kitchen.api.routes import router as kitchen_router
from app.menu.api.price_list_routes import router as price_list_router
from app.menu.api.routes import router as menu_router
from app.order.api.routes import router as order_router
from app.payment.api.routes import router as payment_router
from app.settings import get_settings
from app.shared.database import close_mongo, close_postgres, init_mongo, init_postgres
from app.shared.exceptions import DomainException
from app.shared.logging import setup_logging
from app.shared.tenant_context import tenant_context_var
from app.stock.api.routes import router as stock_router

settings = get_settings()
setup_logging(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize and close database connections."""
    await init_postgres(settings)
    await init_mongo(settings)
    yield
    await close_postgres()
    await close_mongo()


app = FastAPI(
    title="ComandaFácil API",
    description="Sistema de gestão de franquias de food service",
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_origin_regex=r"https?://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tenant_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Inject tenant_id from X-Tenant-ID header into ContextVar."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    if tenant_id and not re.match(r"^[a-zA-Z0-9_-]+$", tenant_id):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Invalid X-Tenant-ID header format. Only alphanumeric characters, hyphens, and underscores are allowed."
            },
        )
    token = tenant_context_var.set(tenant_id)
    try:
        response = await call_next(request)
    finally:
        tenant_context_var.reset(token)
    return response


# ─── Exception Handlers ───────────────────────────────────────────────────────


@app.exception_handler(DomainException)
async def domain_exception_handler(_request: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth_router, prefix="/api/v1")
app.include_router(menu_router, prefix="/api/v1")
app.include_router(order_router, prefix="/api/v1")
app.include_router(kitchen_router, prefix="/api/v1")
app.include_router(payment_router, prefix="/api/v1")
app.include_router(stock_router, prefix="/api/v1")
app.include_router(price_list_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
