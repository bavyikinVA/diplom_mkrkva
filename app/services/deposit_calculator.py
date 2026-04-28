from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.models.deposit_base_rate import DepositBaseRate
from app.models.deposit_bonus_rate import DepositRateBonus, DepositRateBonusCondition
from app.models.deposit_interest_scheme import DepositInterestScheme
from app.models.deposit_variant import DepositVariant
from app.schemas.deposit import AppliedBonusOut, DepositCalculationResult, RateMatchOut


Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")
D365 = Decimal("365")
ONE_HUNDRED = Decimal("100")


def q2(value: Decimal) -> Decimal:
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


def q4(value: Decimal) -> Decimal:
    return value.quantize(Q4, rounding=ROUND_HALF_UP)


@dataclass
class CalculationContext:
    amount: Decimal
    term_days: int
    as_of: date
    open_method_code: str | None = None
    interest_scheme_code: str | None = None

    has_subscription: bool | None = None
    is_salary_client: bool | None = None
    is_pension_client: bool | None = None
    monthly_spend: Decimal | None = None
    savings_balance: Decimal | None = None
    has_premium_package: bool | None = None
    promo_code: str | None = None

    extra_context: dict[str, Any] | None = None

    def to_flat_dict(self) -> dict[str, Any]:
        base = {
            "amount": self.amount,
            "term_days": self.term_days,
            "open_method_code": self.open_method_code,
            "interest_scheme_code": self.interest_scheme_code,
            "has_subscription": self.has_subscription,
            "is_salary_client": self.is_salary_client,
            "is_pension_client": self.is_pension_client,
            "monthly_spend": self.monthly_spend,
            "savings_balance": self.savings_balance,
            "has_premium_package": self.has_premium_package,
            "promo_code": self.promo_code,
        }
        if self.extra_context:
            base.update(self.extra_context)
        return base


class DepositCalculationError(ValueError):
    pass


def _date_matches(
    as_of: date,
    effective_from: date,
    effective_to: date | None,
) -> bool:
    if as_of < effective_from:
        return False
    if effective_to is not None and as_of > effective_to:
        return False
    return True


def _find_open_method_id(
    variant: DepositVariant,
    open_method_code: str | None,
) -> int | None:
    if not open_method_code:
        return None

    for vm in variant.open_methods:
        if (
            vm.open_method
            and vm.open_method.is_active
            and vm.open_method.code == open_method_code
        ):
            return vm.open_method_id

    raise DepositCalculationError(
        f"Способ открытия '{open_method_code}' не поддерживается вариантом вклада"
    )


def _resolve_open_method_code(
    variant: DepositVariant,
    open_method_id: int | None,
) -> str | None:
    if open_method_id is None:
        return None

    for vm in variant.open_methods:
        if vm.open_method_id == open_method_id and vm.open_method:
            return vm.open_method.code

    return None


def _find_scheme(
    variant: DepositVariant,
    interest_scheme_code: str | None,
) -> DepositInterestScheme | None:
    if not interest_scheme_code:
        return None

    for scheme in variant.interest_schemes:
        if scheme.code == interest_scheme_code and scheme.is_active:
            return scheme

    raise DepositCalculationError(
        f"Схема начисления '{interest_scheme_code}' не найдена для варианта вклада"
    )


def _rate_specificity(
    rate: DepositBaseRate,
    selected_scheme_id: int | None,
    selected_open_method_id: int | None,
) -> tuple:
    amount_span = (
        (rate.amount_to - rate.amount_from)
        if rate.amount_to is not None
        else Decimal("999999999999")
    )
    term_span = rate.term_to_days - rate.term_from_days

    return (
        1 if selected_scheme_id is not None and rate.interest_scheme_id == selected_scheme_id else 0,
        1 if selected_open_method_id is not None and rate.open_method_id == selected_open_method_id else 0,
        1 if rate.interest_scheme_id is not None else 0,
        1 if rate.open_method_id is not None else 0,
        -term_span,
        -amount_span,
        rate.effective_from.toordinal(),
        Decimal(str(rate.nominal_rate)),
    )


def select_best_base_rate(
    variant: DepositVariant,
    ctx: CalculationContext,
) -> tuple[DepositBaseRate, DepositInterestScheme | None]:
    selected_open_method_id = _find_open_method_id(variant, ctx.open_method_code)
    selected_scheme = _find_scheme(variant, ctx.interest_scheme_code)
    selected_scheme_id = selected_scheme.id if selected_scheme else None

    candidates: list[DepositBaseRate] = []

    for rate in variant.base_rates:
        if not _date_matches(ctx.as_of, rate.effective_from, rate.effective_to):
            continue

        if ctx.amount < rate.amount_from:
            continue
        if rate.amount_to is not None and ctx.amount > rate.amount_to:
            continue

        if ctx.term_days < rate.term_from_days or ctx.term_days > rate.term_to_days:
            continue

        if (
            selected_open_method_id is not None
            and rate.open_method_id not in (None, selected_open_method_id)
        ):
            continue

        if (
            selected_scheme_id is not None
            and rate.interest_scheme_id not in (None, selected_scheme_id)
        ):
            continue

        candidates.append(rate)

    if not candidates:
        raise DepositCalculationError(
            "Не найдена подходящая базовая ставка для указанных параметров"
        )

    candidates.sort(
        key=lambda r: _rate_specificity(r, selected_scheme_id, selected_open_method_id),
        reverse=True,
    )
    best_rate = candidates[0]

    resolved_scheme = selected_scheme
    if resolved_scheme is None and best_rate.interest_scheme_id is not None:
        resolved_scheme = next(
            (
                s
                for s in variant.interest_schemes
                if s.id == best_rate.interest_scheme_id and s.is_active
            ),
            None,
        )

    return best_rate, resolved_scheme


def _extract_expected(value_json: dict[str, Any]) -> Any:
    if "value" in value_json:
        return value_json["value"]
    return value_json


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "lt":
        return actual is not None and actual < expected
    if operator == "lte":
        return actual is not None and actual <= expected
    if operator == "in":
        return actual in expected if expected is not None else False
    if operator == "not_in":
        return actual not in expected if expected is not None else True
    if operator == "contains":
        return actual is not None and expected in actual
    if operator == "between":
        if not isinstance(expected, dict):
            return False
        low = expected.get("from")
        high = expected.get("to")
        if actual is None:
            return False
        if low is not None and actual < low:
            return False
        if high is not None and actual > high:
            return False
        return True

    raise DepositCalculationError(f"Неподдерживаемый оператор условия: {operator}")


def _condition_matches(
    condition: DepositRateBonusCondition,
    ctx_data: dict[str, Any],
) -> bool:
    actual = ctx_data.get(condition.field_name)
    expected = _extract_expected(condition.value_json)
    return _compare(actual, condition.operator, expected)


def select_applicable_bonuses(
    variant: DepositVariant,
    ctx: CalculationContext,
) -> list[DepositRateBonus]:
    ctx_data = ctx.to_flat_dict()
    matched: list[DepositRateBonus] = []

    for bonus in variant.bonuses:
        if not _date_matches(ctx.as_of, bonus.effective_from, bonus.effective_to):
            continue

        if all(_condition_matches(cond, ctx_data) for cond in bonus.conditions):
            matched.append(bonus)

    stackable = [b for b in matched if b.stackable]
    non_stackable = [b for b in matched if not b.stackable]

    chosen_non_stackable: list[DepositRateBonus] = []
    if non_stackable:
        non_stackable.sort(
            key=lambda b: (b.priority, -Decimal(str(b.bonus_value))),
        )
        chosen_non_stackable = [non_stackable[0]]

    result = stackable + chosen_non_stackable
    result.sort(key=lambda b: (b.priority, -Decimal(str(b.bonus_value))))
    return result


def _periods_per_year(freq: str | None) -> int:
    mapping = {
        "daily": 365,
        "monthly": 12,
        "quarterly": 4,
        "half_year": 2,
        "yearly": 1,
    }
    return mapping.get(freq or "monthly", 12)


def _bonus_to_rate_delta(
    bonus: DepositRateBonus,
    base_nominal_rate: Decimal,
) -> Decimal:
    bonus_value = Decimal(str(bonus.bonus_value))

    if bonus.is_percent_points:
        return q4(bonus_value)

    # интерпретация:
    # если bonus_value НЕ в процентных пунктах,
    # считаем это процентом от базовой ставки
    # например base=20.0, bonus_value=10 => +2.0 п.п.
    return q4(base_nominal_rate * bonus_value / ONE_HUNDRED)


def calculate_interest(
    amount: Decimal,
    term_days: int,
    annual_nominal_rate: Decimal,
    payout_type: str,
    capitalization_enabled: bool,
    capitalization_frequency: str | None,
) -> tuple[Decimal, Decimal]:
    annual_rate_fraction = annual_nominal_rate / ONE_HUNDRED

    if capitalization_enabled:
        periods = _periods_per_year(capitalization_frequency)
        periods_dec = Decimal(periods)
        one_period_days = D365 / periods_dec

        whole_periods = int(Decimal(term_days) / one_period_days)
        remaining_days = Decimal(term_days) - (
            Decimal(whole_periods) * one_period_days
        )

        value = amount * (
            (Decimal("1") + annual_rate_fraction / periods_dec) ** whole_periods
        )

        if remaining_days > 0:
            value *= Decimal("1") + annual_rate_fraction * (remaining_days / D365)

        total_interest = value - amount
        final_amount = value
        return q2(total_interest), q2(final_amount)

    total_interest = amount * annual_rate_fraction * (Decimal(term_days) / D365)

    if payout_type == "end":
        final_amount = amount + total_interest
    else:
        # проценты выплачиваются отдельно, тело вклада не увеличивается
        final_amount = amount

    return q2(total_interest), q2(final_amount)


def build_rate_match_out(
    rate: DepositBaseRate,
    variant: DepositVariant,
) -> RateMatchOut:
    scheme_code = None
    if rate.interest_scheme_id is not None:
        scheme = next(
            (s for s in variant.interest_schemes if s.id == rate.interest_scheme_id),
            None,
        )
        if scheme:
            scheme_code = scheme.code

    open_method_code = _resolve_open_method_code(variant, rate.open_method_id)

    return RateMatchOut(
        base_rate_id=rate.id,
        interest_scheme_id=rate.interest_scheme_id,
        interest_scheme_code=scheme_code,
        open_method_id=rate.open_method_id,
        open_method_code=open_method_code,
        nominal_rate=Decimal(str(rate.nominal_rate)),
        effective_rate=(
            Decimal(str(rate.effective_rate))
            if rate.effective_rate is not None
            else None
        ),
        effective_from=rate.effective_from,
        effective_to=rate.effective_to,
    )


def calculate_variant_result(
    variant: DepositVariant,
    ctx: CalculationContext,
) -> DepositCalculationResult:
    base_rate, scheme = select_best_base_rate(variant, ctx)
    bonuses = select_applicable_bonuses(variant, ctx)

    base_nominal_rate = Decimal(str(base_rate.nominal_rate))

    total_bonus_rate = Decimal("0")
    for bonus in bonuses:
        total_bonus_rate += _bonus_to_rate_delta(bonus, base_nominal_rate)

    total_bonus_rate = q4(total_bonus_rate)
    final_nominal_rate = q4(base_nominal_rate + total_bonus_rate)

    payout_type = scheme.payout_type if scheme else "end"
    capitalization_enabled = scheme.capitalization_enabled if scheme else False
    capitalization_frequency = scheme.capitalization_frequency if scheme else None

    total_interest, final_amount = calculate_interest(
        amount=ctx.amount,
        term_days=ctx.term_days,
        annual_nominal_rate=final_nominal_rate,
        payout_type=payout_type,
        capitalization_enabled=capitalization_enabled,
        capitalization_frequency=capitalization_frequency,
    )

    applied_bonuses = [
        AppliedBonusOut(
            id=bonus.id,
            name=bonus.name,
            bonus_type=(
                bonus.bonus_type.value
                if hasattr(bonus.bonus_type, "value")
                else str(bonus.bonus_type)
            ),
            bonus_value=Decimal(str(bonus.bonus_value)),
            is_percent_points=bonus.is_percent_points,
            stackable=bonus.stackable,
            priority=bonus.priority,
            description=bonus.description,
        )
        for bonus in bonuses
    ]

    resolved_open_method_code = (
        ctx.open_method_code
        or _resolve_open_method_code(variant, base_rate.open_method_id)
    )
    resolved_interest_scheme_code = (
        scheme.code if scheme is not None else ctx.interest_scheme_code
    )

    # effective_rate базы нельзя честно отдавать как итоговую,
    # если были надбавки: это уже другая доходность
    effective_rate_out = None if bonuses else base_rate.effective_rate

    return DepositCalculationResult(
        variant_id=variant.id,
        variant_name=variant.name,
        amount=ctx.amount,
        term_days=ctx.term_days,
        selected_open_method_code=resolved_open_method_code,
        selected_interest_scheme_code=resolved_interest_scheme_code,
        base_nominal_rate=q4(base_nominal_rate),
        final_nominal_rate=final_nominal_rate,
        effective_rate=effective_rate_out,
        total_bonus_rate=total_bonus_rate,
        applied_bonuses=applied_bonuses,
        total_interest=total_interest,
        final_amount=final_amount,
        payout_type=payout_type,
        capitalization_enabled=capitalization_enabled,
        capitalization_frequency=capitalization_frequency,
    )