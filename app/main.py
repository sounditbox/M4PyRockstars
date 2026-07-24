from fastapi import FastAPI

from app.core.config import Settings
from app.dependencies import get_settings
from app.lifespan import lifespan
from app.routers import auth, categories, main, product_attributes, products


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = settings

    application.include_router(
        products.router,
        prefix=settings.api_prefix,
    )
    application.include_router(
        main.router,
        prefix=settings.api_prefix,
    )
    application.include_router(
        categories.router,
        prefix=settings.api_prefix,
    )
    application.include_router(
        auth.router,
        prefix=settings.api_prefix,
    )
    application.include_router(
        product_attributes.router,
        prefix=settings.api_prefix,
    )
    return application


app = create_app()
