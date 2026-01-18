from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlmodel import Session, SQLModel, create_engine
from .core.config import settings
from .routers import auth, regions, me, admin
import os

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

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

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
