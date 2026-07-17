import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.config import get_settings
from app.database import init_db
from app.routers import pages, products, cart, checkout, payments, contact, admin, auth, admin_pages

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.warning("Database not available at startup: %s", e)
        logger.warning("The app will still start, but DB-dependent features will fail until a database is configured")
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.site_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(payments.router)
app.include_router(contact.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(admin_pages.router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "app": settings.app_name, "version": "1.0.0"}
