"""Money value object using integer minor units for exact decimal arithmetic.

Money is never stored as a float. The physical SQLite encoding is two columns:
``*_minor INTEGER`` for the minor-unit amount and ``*_currency TEXT(3)`` for
the ISO 4217 code. The mapper handles encoding and decoding at the storage
boundary; this module is DBMS-agnostic.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Money:
    """Exact monetary amount stored as integer minor units with a currency code.

    Attributes:
        amount_minor: Integer count of minor currency units (e.g., 150 for
            $1.50 USD, where the minor-unit exponent is 2).
        currency: ISO 4217 three-letter uppercase currency code (e.g., ``"USD"``).
    """

    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        """Validate that ``currency`` is a three-letter uppercase ISO 4217 code.

        Raises:
            ValueError: If ``currency`` is not exactly three uppercase letters.
        """
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("currency must be a 3-letter uppercase ISO 4217 code")

    @classmethod
    def from_decimal(cls, amount: Decimal, currency: str, minor_exp: int = 2) -> "Money":
        """Create a ``Money`` instance from a major-unit ``Decimal`` amount.

        Args:
            amount: Major-unit decimal amount (e.g., ``Decimal("1.50")``).
            currency: ISO 4217 three-letter uppercase currency code.
            minor_exp: Exponent of the minor unit relative to the major unit
                (e.g., 2 for USD/EUR, 0 for JPY). Defaults to 2.

        Returns:
            A ``Money`` instance with the amount encoded as integer minor units.

        Raises:
            ValueError: If ``amount`` has more decimal places than ``minor_exp``
                allows, after ROUND_HALF_UP quantisation.
        """
        factor = Decimal(10) ** minor_exp
        minor = int((amount * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cls(amount_minor=minor, currency=currency)

    def to_decimal(self, minor_exp: int = 2) -> Decimal:
        """Convert to a major-unit ``Decimal`` amount.

        Args:
            minor_exp: Exponent used when this value was encoded. Must match
                the value passed to ``from_decimal``. Defaults to 2.

        Returns:
            The major-unit decimal amount.
        """
        return Decimal(self.amount_minor) / (Decimal(10) ** minor_exp)

    def add(self, other: "Money") -> "Money":
        """Return the sum of two same-currency ``Money`` values.

        Args:
            other: Another ``Money`` value with the same currency.

        Returns:
            A new ``Money`` whose ``amount_minor`` is the sum of both operands.

        Raises:
            ValueError: If the two values have different currencies.
        """
        if self.currency != other.currency:
            raise ValueError("cannot add Money values with different currencies")
        return Money(amount_minor=self.amount_minor + other.amount_minor, currency=self.currency)
