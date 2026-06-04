"""Application registry skeleton for preloaded reference/config state."""

from decimal import Decimal
from fractions import Fraction

from thinghound.mappers.attribute_category_mapper import AttributeCategoryMapper
from thinghound.mappers.attribute_definition_mapper import AttributeDefinitionMapper
from thinghound.mappers.prefix_mapper import PrefixMapper
from thinghound.mappers.prefix_set_mapper import PrefixSetMapper
from thinghound.mappers.unit_dimension_mapper import UnitDimensionMapper
from thinghound.mappers.unit_multiplier_mapper import UnitMultiplierMapper
from thinghound.models.schema.attribute_category import AttributeCategory
from thinghound.models.schema.attribute_definition import AttributeDefinition
from thinghound.models.schema.unit_multiplier import UnitMultiplier
from thinghound.session import Session
from thinghound.types import UUIDv7


class RegistryNotLoadedError(RuntimeError):
    """Raised when a registry accessor is used before data is loaded."""


class AppRegistry:
    """Stores application reference/configuration state loaded at startup."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._loaded = False
        self._state: dict[str, object] = {}

    @property
    def is_loaded(self) -> bool:
        """Return whether registry state has been loaded."""
        return self._loaded

    def load(self, state: dict[str, object] | Session) -> None:
        """Load registry state from raw dict or by querying through session mappers."""
        if isinstance(state, Session):
            self._state = self._load_from_session(state)
        else:
            self._state = dict(state)
        self._loaded = True

    def get(self, key: str) -> object:
        """Get a value from loaded registry state.

        Args:
            key: State key.

        Returns:
            Stored value for key.

        Raises:
            RegistryNotLoadedError: If `load` was not called.
            KeyError: If key does not exist.
        """
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry is not loaded")
        return self._state[key]

    def factors_for(self, dimension_id: UUIDv7) -> dict[UUIDv7, Fraction]:
        """Return exact unit factors map for one dimension."""
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry is not loaded")
        factors_by_dimension = self._state.get("factors_by_dimension", {})
        return factors_by_dimension.get(dimension_id, {})

    def _load_from_session(self, session: Session) -> dict[str, object]:
        dimensions = UnitDimensionMapper().list_active(session.connection)
        multipliers = UnitMultiplierMapper().list_active(session.connection)
        prefix_sets = PrefixSetMapper().list_active(session.connection)
        prefixes_by_set = {
            prefix_set.id: PrefixMapper().list_for_prefix_set(session.connection, prefix_set.id)
            for prefix_set in prefix_sets
        }
        attribute_categories = AttributeCategoryMapper().list_active(session.connection)
        attribute_definitions = self._load_attribute_definitions(session, attribute_categories)
        factors_by_dimension = self._build_factors_map(multipliers)

        return {
            "dimensions": dimensions,
            "multipliers": multipliers,
            "prefix_sets": prefix_sets,
            "prefixes_by_set": prefixes_by_set,
            "attribute_categories": attribute_categories,
            "attribute_definitions": attribute_definitions,
            "factors_by_dimension": factors_by_dimension,
        }

    def _load_attribute_definitions(
        self,
        session: Session,
        attribute_categories: list[AttributeCategory],
    ) -> list[AttributeDefinition]:
        definition_mapper = AttributeDefinitionMapper()
        definitions: list[AttributeDefinition] = []
        for category in attribute_categories:
            definitions.extend(
                definition_mapper.list_active_for_category(
                    session.connection,
                    category.id,
                )
            )
        return definitions

    def _build_factors_map(
        self,
        multipliers: list[UnitMultiplier],
    ) -> dict[UUIDv7, dict[UUIDv7, Fraction]]:
        factors_by_dimension: dict[UUIDv7, dict[UUIDv7, Fraction]] = {}
        for multiplier in multipliers:
            dimension_factors = factors_by_dimension.setdefault(multiplier.dimension_id, {})
            dimension_factors[multiplier.id] = self._as_fraction(multiplier.factor)
        return factors_by_dimension

    @staticmethod
    def _as_fraction(value: Decimal) -> Fraction:
        return Fraction(value)
