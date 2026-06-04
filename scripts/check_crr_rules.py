"""Baseline CRR guard checks for ThingHound SQL migrations."""

import re
import sys
from pathlib import Path

FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bAUTOINCREMENT\b", "AUTOINCREMENT is forbidden for CRR compatibility"),
    (r"\bREAL\b", "REAL columns are forbidden; use exact numeric encoding"),
)


def check_sql_text(sql_text: str, path: Path) -> list[str]:
    """Check a SQL string for forbidden CRR patterns.

    Args:
        sql_text: SQL text to inspect.
        path: Source file path for diagnostics.

    Returns:
        List of violation messages.
    """
    violations: list[str] = []
    for pattern, message in FORBIDDEN_PATTERNS:
        if re.search(pattern, sql_text, flags=re.IGNORECASE) is not None:
            violations.append(f"{path}: {message}")
    return violations


def main() -> int:
    """Run CRR checks across migration SQL files.

    Returns:
        Zero on success, non-zero when violations are found.
    """
    migrations_dir = Path("migrations_sql")
    if not migrations_dir.exists():
        print("No migrations_sql directory found; nothing to check.")
        return 0

    violations: list[str] = []
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        violations.extend(check_sql_text(sql_file.read_text(encoding="utf-8"), sql_file))

    if violations:
        for violation in violations:
            print(violation)
        return 1

    print("CRR checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
