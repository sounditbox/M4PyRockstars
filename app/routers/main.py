from fastapi import APIRouter

router = APIRouter(
    tags=["Main/Root/Healthcheck"],
)


@router.get(
    "/", status_code=200, summary="Root endpoint",
    description="Root endpoint description", tags=["Root"]
)
async def root():
    return {"message": "Hello World"}


@router.get("/health", status_code=200, summary="Health endpoint",
            description="Health endpoint description", tags=["Health"])
async def healthcheck():
    return {"status": "ok"}
