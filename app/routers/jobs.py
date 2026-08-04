from typing import Annotated
from uuid import UUID

from celery.exceptions import BackendError
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Path
from kombu.exceptions import OperationalError
from redis.exceptions import RedisError
from starlette.status import HTTP_202_ACCEPTED, HTTP_503_SERVICE_UNAVAILABLE

from app.celery_app import celery_app
from app.schemas import ProductReportRequest, TaskAccepted, TaskStatus
from app.security import AdminRoleDep
from app.tasks import generate_product_report

router = APIRouter(prefix="/jobs", tags=["Background jobs"])


@router.post(
    "/product-reports",
    response_model=TaskAccepted,
    status_code=HTTP_202_ACCEPTED,
)
def start_product_report(
        request: ProductReportRequest,
        _admin: AdminRoleDep,
) -> TaskAccepted:
    try:
        task = generate_product_report.delay(**request.model_dump())
    except OperationalError as exc:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task broker is unavailable",
        ) from exc

    return TaskAccepted(task_id=task.id, status="PENDING")


@router.get("/{task_id}", response_model=TaskStatus)
def get_task_status(
        task_id: Annotated[UUID, Path()],
        _admin: AdminRoleDep,
) -> TaskStatus:
    try:
        task = AsyncResult(str(task_id), app=celery_app)
        status = task.status
        ready = task.ready()
        successful = task.successful() if ready else None
        result = task.result if successful else None
        error = str(task.result) if task.failed() else None
    except (BackendError, RedisError) as exc:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task result backend is unavailable",
        ) from exc

    return TaskStatus(
        task_id=str(task_id),
        status=status,
        ready=ready,
        successful=successful,
        result=result,
        error=error,
    )
