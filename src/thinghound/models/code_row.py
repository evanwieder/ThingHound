"""Shared frozen model for REF code-table rows."""

from pydantic import BaseModel, ConfigDict


class CodeRow(BaseModel):
    """Represents one code-table row with code and label text."""

    model_config = ConfigDict(frozen=True)

    code: str
    label: str
