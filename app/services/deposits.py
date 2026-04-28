from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, exists, func, or_, select, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bank import Bank
from app.models.deposit_base_rate import DepositBaseRate
from app.models.deposit_bonus_rate import DepositRateBonus
from app.models.deposit_interest_scheme import DepositInterestScheme
from app.models.deposit_product import DepositProduct
from app.models.deposit_variant import DepositVariant
from app.models.open_method import DepositOpenMethod, DepositVariantOpenMethod
from app.schemas.deposit import (
    AppliedBonusOut,
    DepositProductOut,
    DepositSearchParams,
    DepositVariantOut,
    DepositsPage,
    InterestSchemeOut,
    OpenMethodOut,
)
from app.services.deposit_calculator import (
    CalculationContext,
    DepositCalculationError,
    build_rate_match_out,
    calculate_variant_result,
    select_best_base_rate,
)


def _base_variant_stmt() -> Select:
    return (
        select(DepositVariant)
        .join(DepositVariant.product)
        .join(DepositProduct.bank)
        .where(
            DepositVariant.is_active.is_(True),
            DepositProduct.is_active.is_(True),
            Bank.is_active.is_(True),
        )
        .options(
            selectinload(DepositVariant.product).selectinload(DepositProduct.bank),
            selectinload(DepositVariant.open_methods).selectinload(
                DepositVariantOpenMethod.open_method
            ),
            selectinload(DepositVariant.interest_schemes),
            selectinload(DepositVariant.base_rates),
            selectinload(DepositVariant.bonuses).selectinload(
                DepositRateBonus.conditions
            ),
        )
    )


def apply_search_filters(stmt: Select, params: DepositSearchParams) -> Select:
    if params.currency:
        stmt = stmt.where(params.currency.upper() == DepositProduct.currency)

    if params.bank_ids:
        stmt = stmt.where(DepositProduct.bank_id.in_(params.bank_ids))

    if params.allow_topup is not None:
        stmt = stmt.where(DepositVariant.allow_topup.is_(params.allow_topup))

    if params.allow_partial_withdraw is not None:
        stmt = stmt.where(
            DepositVariant.allow_partial_withdraw.is_(params.allow_partial_withdraw)
        )

    if params.auto_prolongation is not None:
        stmt = stmt.where(
            DepositVariant.auto_prolongation.is_(params.auto_prolongation)
        )

    if params.amount is not None:
        stmt = stmt.where(
            DepositVariant.min_amount <= params.amount,
            or_(
                DepositVariant.max_amount.is_(None),
                DepositVariant.max_amount >= params.amount,
            ),
        )

    if params.term_days is not None:
        stmt = stmt.where(
            DepositVariant.min_term_days <= params.term_days,
            or_(
                DepositVariant.max_term_days.is_(None),
                DepositVariant.max_term_days >= params.term_days,
            ),
        )

    if params.open_method_codes:
        stmt = stmt.where(
            exists(
                select(1)
                .select_from(DepositVariantOpenMethod)
                .join(
                    DepositOpenMethod,
                    DepositOpenMethod.id == DepositVariantOpenMethod.open_method_id,
                )
                .where(
                    DepositVariantOpenMethod.variant_id == DepositVariant.id,
                    DepositOpenMethod.code.in_(params.open_method_codes),
                    DepositOpenMethod.is_active.is_(True),
                )
            )
        )

    if (
        params.payout_type
        or params.capitalization_enabled is not None
        or params.interest_scheme_code
    ):
        scheme_conditions = [
            DepositInterestScheme.variant_id == DepositVariant.id,
            DepositInterestScheme.is_active.is_(True),
        ]

        if params.payout_type:
            scheme_conditions.append(
                DepositInterestScheme.payout_type == params.payout_type
            )

        if params.capitalization_enabled is not None:
            scheme_conditions.append(
                DepositInterestScheme.capitalization_enabled.is_(
                    params.capitalization_enabled
                )
            )

        if params.interest_scheme_code:
            scheme_conditions.append(
                DepositInterestScheme.code == params.interest_scheme_code
            )

        stmt = stmt.where(
            exists(
                select(1)
                .select_from(DepositInterestScheme)
                .where(and_(*scheme_conditions))
            )
        )

    if params.amount is not None and params.term_days is not None:
        rate_conditions = [
            DepositBaseRate.variant_id == DepositVariant.id,
            DepositBaseRate.amount_from <= params.amount,
            or_(
                DepositBaseRate.amount_to.is_(None),
                DepositBaseRate.amount_to >= params.amount,
            ),
            DepositBaseRate.term_from_days <= params.term_days,
            DepositBaseRate.term_to_days >= params.term_days,
            DepositBaseRate.effective_from <= params.as_of,
            or_(
                DepositBaseRate.effective_to.is_(None),
                DepositBaseRate.effective_to >= params.as_of,
            ),
        ]

        if params.open_method_codes:
            rate_conditions.append(
                or_(
                    DepositBaseRate.open_method_id.is_(None),
                    exists(
                        select(1)
                        .select_from(DepositOpenMethod)
                        .where(
                            DepositOpenMethod.id == DepositBaseRate.open_method_id,
                            DepositOpenMethod.code.in_(params.open_method_codes),
                            DepositOpenMethod.is_active.is_(True),
                        )
                    ),
                )
            )

        if params.interest_scheme_code:
            rate_conditions.append(
                or_(
                    DepositBaseRate.interest_scheme_id.is_(None),
                    exists(
                        select(1)
                        .select_from(DepositInterestScheme)
                        .where(
                            DepositInterestScheme.id
                            == DepositBaseRate.interest_scheme_id,
                            params.interest_scheme_code == DepositInterestScheme.code,
                            DepositInterestScheme.is_active.is_(True),
                        )
                    ),
                )
            )

        stmt = stmt.where(
            exists(
                select(1)
                .select_from(DepositBaseRate)
                .where(and_(*rate_conditions))
            )
        )

    return stmt


def _build_calc_ctx(
    params: DepositSearchParams,
    open_method_code: str | None = None,
) -> CalculationContext:
    return CalculationContext(
        amount=params.amount or Decimal("0"),
        term_days=params.term_days or 0,
        as_of=params.as_of,
        open_method_code=open_method_code,
        interest_scheme_code=params.interest_scheme_code,
        has_subscription=params.has_subscription,
        is_salary_client=params.is_salary_client,
        is_pension_client=params.is_pension_client,
        monthly_spend=params.monthly_spend,
        savings_balance=params.savings_balance,
        has_premium_package=params.has_premium_package,
        promo_code=params.promo_code,
        extra_context=params.extra_context,
    )


def _build_variant_dto(
    variant: DepositVariant,
    matched_rate=None,
    matched_final_nominal_rate=None,
    matched_applied_bonuses: list[AppliedBonusOut] | None = None,
) -> DepositVariantOut:
    bank = variant.product.bank

    open_methods = [
        OpenMethodOut(code=link.open_method.code, name=link.open_method.name)
        for link in variant.open_methods
        if link.open_method and link.open_method.is_active
    ]

    interest_schemes = [
        InterestSchemeOut(
            id=scheme.id,
            code=scheme.code,
            name=scheme.name,
            payout_type=scheme.payout_type,
            payout_frequency=scheme.payout_frequency,
            capitalization_enabled=scheme.capitalization_enabled,
            capitalization_frequency=scheme.capitalization_frequency,
            nominal_rate_only=scheme.nominal_rate_only,
            effective_rate_supported=scheme.effective_rate_supported,
        )
        for scheme in variant.interest_schemes
        if scheme.is_active
    ]

    return DepositVariantOut(
        id=variant.id,
        code=variant.code,
        name=variant.name,
        description=variant.description,
        allow_topup=variant.allow_topup,
        allow_partial_withdraw=variant.allow_partial_withdraw,
        auto_prolongation=variant.auto_prolongation,
        min_amount=variant.min_amount,
        max_amount=variant.max_amount,
        min_term_days=variant.min_term_days,
        max_term_days=variant.max_term_days,
        bank={
            "id": bank.id,
            "name": bank.name,
            "slug": bank.slug,
        },
        product=DepositProductOut(
            id=variant.product.id,
            name=variant.product.name,
            currency=variant.product.currency,
        ),
        open_methods=open_methods,
        interest_schemes=interest_schemes,
        matched_rate=matched_rate,
        matched_final_nominal_rate=matched_final_nominal_rate,
        matched_applied_bonuses=matched_applied_bonuses or [],
    )


async def search_deposit_variants(
    session: AsyncSession,
    params: DepositSearchParams,
) -> DepositsPage:
    base_stmt = apply_search_filters(_base_variant_stmt(), params)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await session.scalar(count_stmt)
    total = total or 0

    stmt = (
        base_stmt.order_by(DepositVariant.id.desc())
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    )

    result = await session.scalars(stmt)
    variants = list(result.unique().all())

    items: list[DepositVariantOut] = []

    for variant in variants:
        matched_rate = None
        matched_final_nominal_rate = None
        matched_bonuses: list[AppliedBonusOut] = []

        if params.amount is not None and params.term_days is not None:
            best_calc = None
            candidate_open_methods = params.open_method_codes or [None]

            for open_method_code in candidate_open_methods:
                try:
                    calc_result = calculate_variant_result(
                        variant,
                        _build_calc_ctx(params, open_method_code),
                    )
                    if (
                        best_calc is None
                        or calc_result.final_nominal_rate > best_calc.final_nominal_rate
                    ):
                        best_calc = calc_result
                except DepositCalculationError:
                    continue

            if best_calc is None:
                continue

            best_rate_obj, _ = select_best_base_rate(
                variant,
                _build_calc_ctx(params, best_calc.selected_open_method_code),
            )

            matched_rate = build_rate_match_out(best_rate_obj, variant)
            matched_final_nominal_rate = best_calc.final_nominal_rate
            matched_bonuses = best_calc.applied_bonuses

        items.append(
            _build_variant_dto(
                variant=variant,
                matched_rate=matched_rate,
                matched_final_nominal_rate=matched_final_nominal_rate,
                matched_applied_bonuses=matched_bonuses,
            )
        )

    if params.amount is not None and params.term_days is not None:
        items.sort(
            key=lambda item: (
                item.matched_final_nominal_rate or Decimal("0"),
                item.matched_rate.nominal_rate if item.matched_rate else Decimal("0"),
            ),
            reverse=True,
        )

    return DepositsPage(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


async def get_variant_or_404(
    session: AsyncSession,
    variant_id: int,
) -> Row[Any] | RowMapping:
    stmt = _base_variant_stmt().where(variant_id == DepositVariant.id)
    result = await session.scalars(stmt)
    variant: Row[Any] | RowMapping | None | Any = result.unique().first()

    if variant is None:
        raise DepositCalculationError("Вариант вклада не найден")

    return variant