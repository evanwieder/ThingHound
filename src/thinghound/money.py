"""Money value object — exact integer minor units, never float."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Money:
    """Exact monetary amount stored as integer minor units + ISO 4217 currency code."""

    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("currency must be a 3-letter uppercase ISO 4217 code")

    @classmethod
    def from_decimal(cls, amount: Decimal, currency: str, minor_exp: int = 2) -> "Money":
        factor = Decimal(10) ** minor_exp
        minor = int((amount * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cls(amount_minor=minor, currency=currency)

    def to_decimal(self, minor_exp: int = 2) -> Decimal:
        return Decimal(self.amount_minor) / (Decimal(10) ** minor_exp)

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("cannot add Money values with different currencies")
        return Money(amount_minor=self.amount_minor + other.amount_minor, currency=self.currency)
