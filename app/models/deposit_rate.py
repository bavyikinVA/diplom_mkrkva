from decimal import Decimal
from datetime import date
from sqlalchemy import ForeignKey, Integer, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DepositRate(Base):
    __tablename__ = "deposit_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("deposit_products.id"),
        nullable=False,
        index=True)

    # Диапазон сумм
    amount_from: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True)

    amount_to: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True)

    # Диапазон сроков
    term_from_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    term_to_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    nominal_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False)

    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    product: Mapped["DepositProduct"] = relationship(back_populates="rates")