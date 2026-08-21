import random

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


@router.get("/random/{number}", status_code=200, summary="Get random number",
            description="Get random number between 0 and number",
            tags=["Random"])
async def random_n(number: int):
    return {"number": random.randint(0, number)}
