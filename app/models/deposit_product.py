from typing import List
from sqlalchemy import (String, Boolean, ForeignKey, Integer, Numeric)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
from app.core.database import Base


class DepositProduct(Base):
    __tablename__ = "deposit_products"

    id: Mapped[int] = mapped_column(primary_key=True)

    bank_id: Mapped[int] = mapped_column(
        ForeignKey("banks.id"),
        nullable=False,
        index=True)

    name: Mapped[str] = mapped_column(String(250), nullable=False)

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="RUB",
        index=True)

    open_methods: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list)

    allow_topup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_withdraw: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    interest_payout: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="end")

    capitalization: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    min_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True)

    max_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True)

    min_term_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_term_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bank: Mapped["Bank"] = relationship(back_populates="products")
    rates: Mapped[List["DepositRate"]] = relationship(back_populates="product")