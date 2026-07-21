from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.dependencies import SessionDep, CategoryDep, get_category_or_404
from app.models import Category, Product
from app.schemas import CategoryCreate, CategoryRead
from app.security import AdminRoleDep

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
        payload: CategoryCreate,
        session: SessionDep,
        _admin: AdminRoleDep,
) -> Category:
    category = Category(**payload.model_dump())
    session.add(category)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Категория с таким name или slug уже существует",
        ) from exc

    session.refresh(category)
    return category


@router.get("", response_model=list[CategoryRead])
async def list_categories(session: SessionDep) -> list[Category]:
    statement = select(Category).order_by(Category.name)
    return list(session.scalars(statement))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    session: SessionDep,
    _admin: AdminRoleDep,
) -> None:
    category = get_category_or_404(category_id, session)

    products_count = session.scalar(
        select(func.count(Product.id)).where(
            Product.category_id == category_id
        )
    )
    if products_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category contains products",
        )

    session.delete(category)
    session.commit()
