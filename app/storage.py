from app.schemas import ProductRead, ProductCreate, UserInDB


class ProductStorage:
    def __init__(self) -> None:
        self.__products: dict[int, ProductRead] = {}
        self._next_id = 1

    def get(self, product_id: int) -> ProductRead | None:
        return self.__products.get(product_id)

    def list(self, limit=None) -> list[ProductRead]:
        if limit:
            return list(self.__products.values())[:limit]
        return list(self.__products.values())

    def delete(self, product_id: int) -> None:
        del self.__products[product_id]

    def clear(self) -> None:
        self.__products.clear()
        self._next_id = 1

    def create(self, product: ProductCreate) -> ProductRead:
        self.__products[self._next_id] = ProductRead(
            id=self._next_id,
            **product.model_dump()
        )
        self._next_id += 1
        return self.__products[self._next_id - 1]

    def set_storage(self, products_data: dict):
        self.__products = products_data
        self._next_id = len(products_data) + 1

    def update(self, product_id, data: ProductCreate):
        self.__products[product_id] = ProductRead(
            id=product_id,
            **data.model_dump()
        )
        return self.__products[product_id]


class UserStorage:
    def __init__(self) -> None:
        self.users: dict[int, UserInDB] = {}

    def add(self, user: UserInDB) -> None:
        self.users[user.id] = user

    def get(self, user_id: int) -> UserInDB | None:
        return self.users.get(user_id)

    def get_by_username(self, username: str) -> UserInDB | None:
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def set_storage(self, users_data: list):
        self.users = {user.id: user for user in users_data}

    def clear(self) -> None:
        self.users.clear()