from __future__ import annotations
from typing import Union

from decimal import Decimal, ROUND_HALF_UP


Numeric = Union[Decimal, int, float, str]


def num(value: Numeric) -> Decimal:
    value = Decimal(value)
    if not value.is_finite():
        raise ValueError("expected finite amount")
    if value < 0:
        raise ValueError("expected non-negative amount")
    return value


def num_string(value: Decimal) -> str:
    decimals = max(0, min(2, 3 - len(str(int(value)))))
    rounded = value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    if decimals == 0:
        return f"{rounded:f}"
    return f"{rounded:f}".rstrip("0").rstrip(".")


def exact_string(value: Decimal) -> str:
    return f"{value.normalize():f}"


def json_number(value: Decimal) -> Union[int, float]:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def amount_string(amount: str, unit: str) -> str:
    if unit[:1].isdigit():
        return f"{amount} × {unit}"
    return f"{amount} {unit}".strip()


def metric_strings(values: dict[str, Decimal], per: str = "") -> list[str]:
    return [f"{num_string(value)} {metric}{per}" for metric, value in values.items()]
