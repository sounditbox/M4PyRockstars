from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, relationship

from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Integer,
    MetaData,
    Numeric,
    String, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": (
        "fk_%(table_name)s_%(column_0_name)s_"
        "%(referred_table_name)s"
    ),
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(80), index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sale_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    stock_count: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint(
            "stock_count >= 0",
            name="ck_products_stock_count_nonnegative",
        ),
        default=0,
        server_default="0",
    )
    specs: Mapped[dict[str, object] | None] = mapped_column(
        JSON, nullable=True
    )

    category: Mapped[Category] = relationship(
        back_populates="products"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(80), unique=True, index=True
    )
    slug: Mapped[str] = mapped_column(
        String(40), unique=True, index=True
    )

    products: Mapped[list[Product]] = relationship(
        back_populates="category"
    )
