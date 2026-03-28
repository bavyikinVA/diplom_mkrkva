from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.deposit import DepositsPage, DepositOut
from app.services.deposits import get_deposits

router = APIRouter(prefix="/api", tags=["deposits"])


@router.get("/deposits", response_model=DepositsPage)
async def list_deposits(
    amount: Decimal | None = Query(default=None, gt=0),
    term_days: int | None = Query(default=None, gt=0),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    bank_ids: list[int] | None = Query(default=None),
    allow_topup: bool | None = Query(default=None),
    allow_withdraw: bool | None = Query(default=None),
    open_method: str | None = Query(default=None),
    interest_payout: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    rows, total = await get_deposits(
        session,
        amount=amount,
        term_days=term_days,
        currency=currency,
        bank_ids=bank_ids,
        allow_topup=allow_topup,
        allow_withdraw=allow_withdraw,
        open_method=open_method,
        interest_payout=interest_payout,
        page=page,
        page_size=page_size,
    )

    items: list[DepositOut] = []
    for product, bank, matched_rate in rows:
        dto = DepositOut.model_validate(product)
        dto.bank = dto.bank.model_validate(bank) if hasattr(dto, "bank") else bank  # страховка
        dto.bank = type(dto.bank).model_validate(bank)  # нормальная подстановка
        dto.matched_rate = matched_rate
        items.append(dto)

    return DepositsPage(items=items, total=total, page=page, page_size=page_size)