from __future__ import annotations

from typing import Annotated, Self, Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator, \
    model_validator

ProductName = Annotated[
    str, Field(min_length=3, max_length=80, examples=["Mechanical Keyboard"]),
]
CategoryName = Annotated[
    str, Field(min_length=2, max_length=40, pattern=r"^[a-zA-Z0-9-]+$"),
]
PositivePrice = Annotated[float, Field(gt=0, le=1_000_000)]
StockCount = Annotated[int, Field(ge=0)]
Tag = Annotated[str, Field(min_length=2, max_length=30)]

CategoryId = Annotated[int, Field(gt=0)]
CategoryTitle = Annotated[
    str, Field(min_length=2, max_length=80)
]
CategorySlug = Annotated[
    str,
    Field(min_length=2, max_length=40, pattern=r"^[a-z0-9-]+$"),
]


class CategoryBase(BaseModel):
    name: CategoryTitle
    slug: CategorySlug


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProductSpecs(BaseModel):
    weight_grams: int = Field(gt=0)
    color: str | None = Field(default=None, max_length=30)
    tags: list[Tag] = Field(default_factory=list, max_length=10)


class ProductBase(BaseModel):
    title: ProductName
    price: PositivePrice
    description: str | None = Field(default=None, max_length=500)
    is_available: bool = True
    specs: ProductSpecs | None = None
    sale_price: PositivePrice | None = None
    stock_count: StockCount = 0

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if normalized.lower() in {"test", "product", "товар"}:
            raise ValueError("Укажите содержательное название товара")
        return normalized


class ProductCreate(ProductBase):
    category_id: CategoryId

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True,
    )

    @model_validator(mode="after")
    def check_sale_price(self) -> Self:
        if self.sale_price is not None and self.sale_price >= self.price:
            raise ValueError(
                "Цена со скидкой должна быть меньше обычной цены"
            )
        return self


class ProductUpdate(BaseModel):
    title: ProductName | None = None
    category_id: CategoryId | None = None
    price: PositivePrice | None = None
    description: str | None = Field(default=None, max_length=500)
    is_available: bool | None = None
    specs: ProductSpecs | None = None
    sale_price: PositivePrice | None = None
    stock_count: StockCount | None = None

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ProductRead(ProductBase):
    id: int
    category: CategoryRead
    model_config = ConfigDict(from_attributes=True)


class ProductInternal(ProductRead):
    supplier_code: str
    purchase_price: PositivePrice


Role = Literal["user", "admin"]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role = "user"
    disabled: bool = False


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    type: Literal["access"]
