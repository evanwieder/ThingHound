"""Money value object using minor integer units for exactness."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Money:
    """Represents an exact monetary amount in minor units.

    Args:
        amount_minor: Integer count of minor currency units.
        currency: Three-letter uppercase ISO currency code.
    """

    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        """Validate currency format.

        Raises:
            ValueError: If the currency code is invalid.
        """
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("Currency must be a 3-letter uppercase code")

    @classmethod
    def from_decimal(cls, amount: Decimal, currency: str, minor_exp: int = 2) -> "Money":
        """Create a Money value from a decimal amount.

        Args:
            amount: Decimal major-unit amount.
            currency: Three-letter uppercase currency code.
            minor_exp: Decimal exponent for minor units.

        Returns:
            Money encoded in minor units.
        """
        factor = Decimal(10) ** minor_exp
        quantized = (amount * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return cls(amount_minor=int(quantized), currency=currency)

    def to_decimal(self, minor_exp: int = 2) -> Decimal:
        """Convert to a Decimal major-unit amount.

        Args:
            minor_exp: Decimal exponent for minor units.

        Returns:
            Decimal monetary amount.
        """
        return Decimal(self.amount_minor) / (Decimal(10) ** minor_exp)

    def add(self, other: "Money") -> "Money":
        """Add money values with matching currencies.

        Args:
            other: Other money value.

        Returns:
            Sum money value.

        Raises:
            ValueError: If currencies do not match.
        """
        if self.currency != other.currency:
            raise ValueError("Cannot add money values with different currencies")
        return Money(amount_minor=self.amount_minor + other.amount_minor, currency=self.currency)
