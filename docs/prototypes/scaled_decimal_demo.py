#!/usr/bin/env python3
"""
Prototype: scaled-integer-per-dimension exact storage for ThingHound.

Proves the proposed replacement for `value_num REAL`:
  - value_exact  TEXT     : canonical decimal, lossless (source of truth)
  - value_scaled INTEGER  : round(value_base * 10**scale), exact, B-tree indexable

Conversion math is done with `fractions.Fraction` (perfectly exact rationals),
NOT float. This is the key correctness point: a float path (Pint's default,
or a REAL column) cannot represent most of these values exactly.

Stdlib only: fractions, decimal, sqlite3. No third-party deps.
"""

from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, getcontext
from fractions import Fraction
import sqlite3
import unicodedata

getcontext().prec = 50
INT64_MAX = 2**63 - 1


# --------------------------------------------------------------------------
# Dimension registry: base unit, chosen scale (decimal places in base unit),
# and EXACT unit->base factors as rationals.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Dimension:
    name: str
    base_unit: str
    scale: int                       # decimal places kept in the base unit
    factors: dict[str, Fraction]     # unit symbol -> exact factor to base


DIMENSIONS = {
    "resistance": Dimension("resistance", "ohm", 6, {
        "ohm": Fraction(1), "Ω": Fraction(1), "R": Fraction(1),
        "mΩ": Fraction(1, 1000), "kΩ": Fraction(1000), "k": Fraction(1000),
        "MΩ": Fraction(10**6), "µΩ": Fraction(1, 10**6),
    }),
    "capacitance": Dimension("capacitance", "farad", 15, {
        "F": Fraction(1), "mF": Fraction(1, 10**3), "µF": Fraction(1, 10**6),
        "uF": Fraction(1, 10**6), "nF": Fraction(1, 10**9),
        "pF": Fraction(1, 10**12),
    }),
    "power": Dimension("power", "watt", 6, {
        "W": Fraction(1), "watt": Fraction(1), "mW": Fraction(1, 1000),
        "kW": Fraction(1000),
    }),
    "length": Dimension("length", "metre", 9, {
        "m": Fraction(1), "cm": Fraction(1, 100), "mm": Fraction(1, 1000),
        "in": Fraction(127, 5000), "inch": Fraction(127, 5000),  # 0.0254 m exact
    }),
}

VULGAR = {  # unicode vulgar fractions -> exact rationals
    "½": Fraction(1, 2), "¼": Fraction(1, 4), "¾": Fraction(3, 4),
    "⅓": Fraction(1, 3), "⅔": Fraction(2, 3), "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8), "⅝": Fraction(5, 8), "⅞": Fraction(7, 8),
}


# --------------------------------------------------------------------------
# Fraction-aware magnitude parser.
# Handles: decimals (.5, 1.0625), integers, vulgar (½), slash (1/2),
# mixed numbers (1-1/16, 1 1/16, 1+1/16, 1½).
# Returns an EXACT Fraction.
# --------------------------------------------------------------------------
def parse_magnitude(tok: str) -> Fraction:
    tok = tok.strip()
    # trailing vulgar glyph, possibly with a leading integer: "1½"
    if tok and tok[-1] in VULGAR:
        whole = tok[:-1].strip() or "0"
        return Fraction(int(whole)) + VULGAR[tok[-1]]
    if tok in VULGAR:
        return VULGAR[tok]
    # normalize mixed-number separators "1-1/16" / "1+1/16" / "1 1/16" -> parts
    norm = tok.replace("+", " ").replace("-", " ")
    parts = norm.split()
    if len(parts) == 2 and "/" in parts[1]:        # mixed number
        n, d = parts[1].split("/")
        return Fraction(int(parts[0])) + Fraction(int(n), int(d))
    if len(parts) == 1 and "/" in parts[0]:        # pure slash fraction
        n, d = parts[0].split("/")
        return Fraction(int(n), int(d))
    # plain decimal / integer -> exact via Decimal
    return Fraction(Decimal(tok))


def split_input(raw: str) -> tuple[str, str]:
    """Split 'magnitude unit' tolerating no space: '1kΩ', '100 pF', '½ W'."""
    raw = unicodedata.normalize("NFC", raw).strip()
    # walk from the end while chars look like a unit (letters / Ω / µ)
    i = len(raw)
    while i > 0 and (raw[i-1].isalpha() or raw[i-1] in "ΩµR"):
        i -= 1
    mag, unit = raw[:i].strip(), raw[i:].strip()
    return mag, unit


# --------------------------------------------------------------------------
# Normalization: raw input -> (value_exact TEXT, value_scaled INTEGER).
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Normalized:
    dimension: str
    value_raw: str
    base_fraction: Fraction      # exact base-unit value (rational)
    value_exact: str             # canonical decimal text (storage)
    value_scaled: int            # indexed integer (storage)
    exact_scaling: bool          # True iff scaling lost nothing


def normalize(raw: str, dim_name: str) -> Normalized:
    dim = DIMENSIONS[dim_name]
    mag, unit = split_input(raw)
    if unit not in dim.factors:
        raise ValueError(f"unknown unit {unit!r} for {dim_name}")
    base = parse_magnitude(mag) * dim.factors[unit]          # exact rational

    scaled_rational = base * (10 ** dim.scale)
    value_scaled = round(scaled_rational)                    # nearest int
    exact_scaling = (scaled_rational.denominator == 1)       # lost nothing?

    # canonical decimal text at the dimension's resolution
    value_exact = str(Decimal(base.numerator) / Decimal(base.denominator))

    if abs(value_scaled) > INT64_MAX:
        raise OverflowError(f"{raw} exceeds int64 at scale {dim.scale}")
    return Normalized(dim_name, raw, base, value_exact, value_scaled, exact_scaling)


def scaled_to_base(value_scaled: int, dim_name: str) -> Fraction:
    return Fraction(value_scaled, 10 ** DIMENSIONS[dim_name].scale)


# ==========================================================================
# DEMONSTRATIONS
# ==========================================================================
def hr(t): print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


def demo_roundtrip():
    hr("1. EXACT ROUND-TRIP  (raw -> base -> scaled int -> base)")
    cases = [
        ("100 pF", "capacitance"), ("2.2 nF", "capacitance"),
        ("1 kΩ", "resistance"),    ("4700 Ω", "resistance"),
        ("½ W", "power"),          (".5 W", "power"),
        ("1-1/16 in", "length"),   ("2 cm", "length"),
    ]
    print(f"{'input':<12}{'base (exact)':<22}{'value_exact':<14}"
          f"{'value_scaled':>16}  exact")
    for raw, dim in cases:
        n = normalize(raw, dim)
        rt = scaled_to_base(n.value_scaled, dim)
        ok = "✓" if rt == n.base_fraction else "✗ MISMATCH"
        print(f"{raw:<12}{str(n.base_fraction)+' '+DIMENSIONS[dim].base_unit:<22}"
              f"{n.value_exact:<14}{n.value_scaled:>16}  {ok}")


def demo_equality():
    hr("2. EQUALITY ON value_exact / value_scaled  (½ W == .5 W)")
    a, b = normalize("½ W", "power"), normalize(".5 W", "power")
    print(f"  ½ W  -> exact={a.value_exact!r} scaled={a.value_scaled}")
    print(f"  .5 W -> exact={b.value_exact!r} scaled={b.value_scaled}")
    print(f"  equal? exact={a.value_exact == b.value_exact} "
          f"scaled={a.value_scaled == b.value_scaled}")


def demo_ordering_and_range():
    hr("3. SQLITE: integer index gives correct ordering + range queries")
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE v(
        item TEXT, dimension TEXT,
        value_scaled INTEGER NOT NULL, value_exact TEXT NOT NULL)""")
    con.execute("CREATE INDEX ix ON v(dimension, value_scaled)")
    rows = [("R-a", "1 kΩ"), ("R-b", "2000 Ω"), ("R-c", "1.2 kΩ"),
            ("R-d", "1.5 kΩ"), ("R-e", "999 Ω"), ("R-f", "470 Ω")]
    for item, raw in rows:
        n = normalize(raw, "resistance")
        con.execute("INSERT INTO v VALUES(?,?,?,?)",
                    (item, "resistance", n.value_scaled, n.value_exact))

    print("  ORDER BY value_scaled  (note 1 kΩ < 2000 Ω):")
    for item, exact in con.execute(
            "SELECT item, value_exact FROM v WHERE dimension='resistance' "
            "ORDER BY value_scaled"):
        print(f"    {item}  {exact} ohm")

    lo = normalize("1 kΩ", "resistance").value_scaled
    hi = normalize("1.5 kΩ", "resistance").value_scaled
    print(f"\n  RANGE 1kΩ..1.5kΩ  (indexed: value_scaled BETWEEN {lo} AND {hi}):")
    for item, exact in con.execute(
            "SELECT item, value_exact FROM v WHERE dimension='resistance' "
            "AND value_scaled BETWEEN ? AND ? ORDER BY value_scaled", (lo, hi)):
        print(f"    {item}  {exact} ohm")

    # cross-unit ordering sanity: 2 cm < 1-1/16 in
    for item, raw in [("L-2cm", "2 cm"), ("L-1in16", "1-1/16 in")]:
        n = normalize(raw, "length")
        con.execute("INSERT INTO v VALUES(?,?,?,?)",
                    (item, "length", n.value_scaled, n.value_exact))
    print("\n  length ORDER BY value_scaled (2 cm < 1-1/16 in):")
    for item, exact in con.execute(
            "SELECT item, value_exact FROM v WHERE dimension='length' "
            "ORDER BY value_scaled"):
        print(f"    {item}  {exact} m")
    con.close()


def demo_headroom():
    hr("4. INT64 HEADROOM per dimension (scale vs realistic max)")
    realistic = {"resistance": ("1 TΩ", Fraction(10**12)),
                 "capacitance": ("3000 F supercap", Fraction(3000)),
                 "power": ("1 GW", Fraction(10**9)),
                 "length": ("1 km", Fraction(1000))}
    print(f"{'dimension':<13}{'scale':>6}{'max base @int64':>22}"
          f"{'realistic max':>18}  fits")
    for name, dim in DIMENSIONS.item():
        max_base = Fraction(INT64_MAX, 10 ** dim.scale)
        label, rmax = realistic[name]
        fits = "✓" if rmax <= max_base else "✗"
        print(f"{name:<13}{dim.scale:>6}{float(max_base):>22.3e}"
              f"{label:>18}  {fits}")


def demo_real_fails():
    hr("5. WHY NOT REAL: float loses exactness where int/decimal do not")
    # classic decimal sum
    print("  float : 0.1 + 0.2 == 0.3  ->", (0.1 + 0.2) == 0.3)
    print("  Decimal: 0.1 + 0.2 == 0.3 ->",
          (Decimal('0.1') + Decimal('0.2')) == Decimal('0.3'))
    # capacitance: sum of 0.1 pF a thousand times should be exactly 100 pF
    scale = DIMENSIONS["capacitance"].scale
    one_tenth_pF = normalize("0.1 pF", "capacitance").value_scaled
    total_scaled = one_tenth_pF * 1000
    target = normalize("100 pF", "capacitance").value_scaled
    print(f"\n  Σ(0.1 pF ×1000) via scaled int == 100 pF ? "
          f"{total_scaled == target}  ({total_scaled} == {target})")
    f = 0.1e-12
    print(f"  Σ(0.1 pF ×1000) via float        == 100 pF ? "
          f"{(f * 1000) == 100e-12}  ({f*1000!r})")


if __name__ == "__main__":
    demo_roundtrip()
    demo_equality()
    demo_ordering_and_range()
    demo_headroom()
    demo_real_fails()
    print("\n" + "=" * 72)
    print("Done. value_exact = lossless truth; value_scaled = exact int index.")
    print("=" * 72)
