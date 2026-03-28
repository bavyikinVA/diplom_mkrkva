from decimal import Decimal
from app.schemas.common import ORMBase
from app.schemas.bank import BankOut


class DepositOut(ORMBase):
    id: int
    name: str
    currency: str
    open_methods: list[str]
    allow_topup: bool
    allow_withdraw: bool
    interest_payout: str
    capitalization: bool
    min_amount: Decimal | None
    max_amount: Decimal | None
    min_term_days: int | None
    max_term_days: int | None
    is_active: bool

    bank: BankOut

    # если запрос передал amount+term_days — вернём подобранную ставку
    matched_rate: Decimal | None = None


class DepositsPage(ORMBase):
    items: list[DepositOut]
    total: int
    page: int
    page_size: int