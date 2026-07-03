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
Tag = Annotated[str, Field(min_length=2, max_length=30)]


class ProductSpecs(BaseModel):
    weight_grams: int = Field(gt=0)
    color: str | None = Field(default=None, max_length=30)
    tags: list[Tag] = Field(default_factory=list, max_length=10)


class ProductBase(BaseModel):
    name: ProductName
    category: CategoryName
    price: PositivePrice
    description: str | None = Field(default=None, max_length=500)
    is_available: bool = True
    specs: ProductSpecs | None = None
    sale_price: PositivePrice | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())

        if normalized.lower() in {"test", "product", "товар"}:
            raise ValueError("Укажите содержательное название товара")

        return normalized


class ProductCreate(ProductBase):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def check_sale_price(self) -> Self:
        if self.sale_price is not None and self.sale_price >= self.price:
            raise ValueError("Цена со скидкой должна быть меньше обычной цены")

        return self


class ProductUpdate(BaseModel):
    name: ProductName | None = None
    category: CategoryName | None = None
    price: PositivePrice | None = None
    description: str | None = Field(default=None, max_length=500)
    is_available: bool | None = None


class ProductRead(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProductInternal(ProductRead):
    supplier_code: str
    purchase_price: PositivePrice


Role = Literal["user", "admin"]


class UserRead(BaseModel):
    id: int
    username: str
    role: Role = "user"
    disabled: bool = False


class UserInDB(UserRead):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    type: Literal["access"]
