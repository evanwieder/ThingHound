"""Schema service for dimensions, categories, and resolved schema reads."""

from thinghound.mappers.attribute_category_mapper import AttributeCategoryMapper
from thinghound.mappers.attribute_definition_mapper import AttributeDefinitionMapper
from thinghound.mappers.unit_dimension_mapper import UnitDimensionMapper
from thinghound.models.read_model.attribute_schema import AttributeSchema
from thinghound.models.schema.attribute_category import AttributeCategory
from thinghound.models.schema.unit_dimension import UnitDimension
from thinghound.queries.schema_resolution_query import SchemaResolutionQuery
from thinghound.session import Session
from thinghound.types import UUIDv7


class DuplicateAttributeNameError(ValueError):
    """Raised when attribute name duplicates within one attribute category."""


class SchemaService:
    """Orchestrates schema mappers and query objects without owning SQL."""

    def __init__(
        self,
        unit_dimension_mapper: UnitDimensionMapper,
        attribute_category_mapper: AttributeCategoryMapper,
        attribute_definition_mapper: AttributeDefinitionMapper,
        schema_resolution_query: SchemaResolutionQuery,
    ) -> None:
        self._unit_dimension_mapper = unit_dimension_mapper
        self._attribute_category_mapper = attribute_category_mapper
        self._attribute_definition_mapper = attribute_definition_mapper
        self._schema_resolution_query = schema_resolution_query

    def get_dimensions(self, session: Session) -> list[UnitDimension]:
        """Return active dimensions for schema APIs."""
        return self._unit_dimension_mapper.list_active(session.connection)

    def get_attribute_categories(self, session: Session) -> list[AttributeCategory]:
        """Return active attribute categories for schema APIs."""
        return self._attribute_category_mapper.list_active(session.connection)

    def get_resolved_schema(self, session: Session, category_id: UUIDv7) -> list[AttributeSchema]:
        """Return resolved schema for one category id."""
        return self._schema_resolution_query.resolve(session.connection, category_id)

    def assert_unique_name_within_category(
        self,
        *,
        session: Session,
        attribute_category_id: UUIDv7,
        name: str,
    ) -> None:
        """Enforce uniqueness of `(name, attribute_category_id)` across active attributes."""
        existing = self._attribute_definition_mapper.list_active_for_category(
            session.connection,
            attribute_category_id,
        )
        lowered_name = name.casefold()
        if any(definition.name.casefold() == lowered_name for definition in existing):
            raise DuplicateAttributeNameError(
                f"Attribute '{name}' already exists in category {attribute_category_id}"
            )


def default_schema_service() -> SchemaService:
    """Build schema service with default U1 mappers/query."""
    return SchemaService(
        unit_dimension_mapper=UnitDimensionMapper(),
        attribute_category_mapper=AttributeCategoryMapper(),
        attribute_definition_mapper=AttributeDefinitionMapper(),
        schema_resolution_query=SchemaResolutionQuery(),
    )
