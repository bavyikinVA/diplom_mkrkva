from app.schemas.common import ORMBase


class BankOut(ORMBase):
    id: int
    name: str
    slug: str
    is_active: bool