"""Tests for shared code-table model."""

import pytest

from thinghound.models.code_row import CodeRow


def test_code_row_is_frozen() -> None:
    """CodeRow should be immutable once created."""
    row = CodeRow(code="x", label="X")
    with pytest.raises(Exception):
        row.code = "y"
