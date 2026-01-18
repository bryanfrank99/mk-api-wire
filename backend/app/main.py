from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel import Session, SQLModel, create_engine
from .core.config import settings
from .routers import auth, regions, me, admin
from .core.audit_logging import configure_audit_logging, set_audit_context, reset_audit_context
import os
import logging
from uuid import UUID

# Database setup
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gate non-admin API routes by client version.
# This keeps the browser-based admin UI working while forcing the desktop client to update.
@app.middleware("http")
async def enforce_client_version(request: Request, call_next):
    path = request.url.path

    if path.startswith(settings.API_V1_STR):
        # Allow admin endpoints (used by the Admin UI in a browser).
        if path.startswith(f"{settings.API_V1_STR}/admin"):
            return await call_next(request)

        # Allow auth endpoints (Admin UI login uses /auth/login).
        if path.startswith(f"{settings.API_V1_STR}/auth"):
            return await call_next(request)

        # Allow OpenAPI for debugging.
        if path == f"{settings.API_V1_STR}/openapi.json":
            return await call_next(request)

        client_version = request.headers.get("X-Client-Version")
        if client_version != settings.REQUIRED_CLIENT_VERSION:
            return JSONResponse(
                status_code=426,
                headers={"X-Required-Client-Version": settings.REQUIRED_CLIENT_VERSION},
                content={
                    "detail": "Client version not supported",
                    "required_version": settings.REQUIRED_CLIENT_VERSION,
                    "provided_version": client_version,
                },
            )

    return await call_next(request)


@app.middleware("http")
async def audit_request_logs(request: Request, call_next):
    # Attach minimal context so audit log records can be attributed.
    token = None
    token_path = None
    try:
        path = request.url.path
        user_id = None

        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            try:
                from jose import jwt
                from .core.security import ALGORITHM

                token_str = auth.split(" ", 1)[1].strip()
                payload = jwt.decode(token_str, settings.SECRET_KEY, algorithms=[ALGORITHM])
                sub = payload.get("sub")
                if sub:
                    user_id = UUID(str(sub))
            except Exception:
                user_id = None

        token, token_path = set_audit_context(user_id=user_id, path=path)

        logging.info("HTTP %s %s", request.method, path)
        response = await call_next(request)
        logging.info("HTTP %s %s -> %s", request.method, path, getattr(response, "status_code", "?"))
        return response
    finally:
        if token is not None and token_path is not None:
            reset_audit_context(token, token_path)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    configure_audit_logging(engine)

# Serve Admin UI
# Ensure the directory exists
static_path = os.path.join(os.path.dirname(__file__), "..", "static", "admin")
if os.path.exists(static_path):
    app.mount("/admin-ui", StaticFiles(directory=static_path), name="admin-ui")

@app.get("/admin")
async def admin_redirect():
    return RedirectResponse(url="/admin-ui/index.html")

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(regions.router, prefix=f"{settings.API_V1_STR}/regions", tags=["regions"])
app.include_router(me.router, prefix=f"{settings.API_V1_STR}/me", tags=["me"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])

@app.get("/")
def root():
    return {"message": "WireGuard Account Manager API is running", "v": "1.0.0"}
