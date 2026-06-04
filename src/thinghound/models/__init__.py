"""Domain model package: frozen Pydantic entities and value objects.

Each entity lives in its own file under a domain-named subdirectory (e.g.,
``models/schema/unit_dimension.py``). Models are DBMS-agnostic — they hold
domain types (``Decimal``, ``Money``, ``UUIDv7``, ISO-8601 strings) and know
nothing about SQLite column encodings or row formats. All physical encoding
and decoding is the aggregate mapper's responsibility.
"""
