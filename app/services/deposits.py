from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank import Bank
from app.models.deposit_product import DepositProduct
from app.models.deposit_rate import DepositRate


def _matched_rate_subquery(amount: Decimal, term_days: int):
    """
    Коррелированный subquery:
    берём максимальную ставку, которая подходит под amount и term_days.
    """
    conds = [
        DepositRate.product_id == DepositProduct.id,

        # amount in [amount_from, amount_to] с учётом NULL границ
        func.coalesce(DepositRate.amount_from, Decimal("0")) <= amount,
        func.coalesce(DepositRate.amount_to, Decimal("9999999999999999")) >= amount,

        # term in [term_from_days, term_to_days] с учётом NULL границ
        func.coalesce(DepositRate.term_from_days, 0) <= term_days,
        func.coalesce(DepositRate.term_to_days, 10**9) >= term_days,
    ]

    return (
        select(DepositRate.nominal_rate)
        .where(and_(*conds))
        .order_by(DepositRate.nominal_rate.desc())
        .limit(1)
        .scalar_subquery()
    )


async def get_deposits(
    session: AsyncSession,
    *,
    amount: Decimal | None = None,
    term_days: int | None = None,
    currency: str | None = None,
    bank_ids: list[int] | None = None,
    allow_topup: bool | None = None,
    allow_withdraw: bool | None = None,
    open_method: str | None = None,
    interest_payout: str | None = None,
    is_active: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[DepositProduct, Bank, Decimal | None]], int]:
    """
    Возвращает:
      items: список (product, bank, matched_rate)
      total: общее число продуктов после фильтров (без пагинации)
    """

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    # matched_rate (опционально)
    matched_rate_expr = None
    if amount is not None and term_days is not None:
        matched_rate_expr = _matched_rate_subquery(amount, term_days).label("matched_rate")
    else:
        matched_rate_expr = func.cast(None, DepositRate.nominal_rate.type).label("matched_rate")

    q = (
        select(DepositProduct, Bank, matched_rate_expr)
        .join(Bank, Bank.id == DepositProduct.bank_id)
    )

    filters = []

    if is_active:
        filters.append(DepositProduct.is_active.is_(True))
        filters.append(Bank.is_active.is_(True))

    if currency:
        filters.append(DepositProduct.currency == currency)

    if bank_ids:
        filters.append(DepositProduct.bank_id.in_(bank_ids))

    if allow_topup is not None:
        filters.append(DepositProduct.allow_topup.is_(allow_topup))

    if allow_withdraw is not None:
        filters.append(DepositProduct.allow_withdraw.is_(allow_withdraw))

    if interest_payout:
        filters.append(DepositProduct.interest_payout == interest_payout)

    if open_method:
        # JSONB array contains value: ["online"] ⊆ open_methods
        filters.append(DepositProduct.open_methods.contains([open_method]))

    if filters:
        q = q.where(and_(*filters))

    # Если передали amount/term_days — можно дополнительно отсечь продукты по min/max продукта
    if amount is not None:
        q = q.where(
            and_(
                func.coalesce(DepositProduct.min_amount, Decimal("0")) <= amount,
                func.coalesce(DepositProduct.max_amount, Decimal("9999999999999999")) >= amount,
            )
        )
    if term_days is not None:
        q = q.where(
            and_(
                func.coalesce(DepositProduct.min_term_days, 0) <= term_days,
                func.coalesce(DepositProduct.max_term_days, 10**9) >= term_days,
            )
        )

    # total count
    count_q = select(func.count()).select_from(
        select(DepositProduct.id).select_from(DepositProduct).join(Bank).where(and_(*filters))  # type: ignore
        .distinct()
        .subquery()
    )
    total = (await session.execute(count_q)).scalar_one()

    # paging + сортировка:
    # если есть matched_rate — сортируем по ней (desc), иначе по id
    if amount is not None and term_days is not None:
        q = q.order_by(matched_rate_expr.desc().nullslast(), DepositProduct.id.asc())
    else:
        q = q.order_by(DepositProduct.id.asc())

    q = q.limit(page_size).offset(offset)

    rows: Sequence[tuple[DepositProduct, Bank, Decimal | None]] = (await session.execute(q)).all()
    return list(rows), total