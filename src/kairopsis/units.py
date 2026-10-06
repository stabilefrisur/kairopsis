"""Small deterministic unit algebra; supplied units stay opaque, without conversion."""
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    powers: tuple[tuple[str, int], ...] = ()

    @classmethod
    def supplied(cls, label: str) -> "Unit":
        return cls(((label, 1),))

    def combine(self, other: "Unit", sign: int = 1) -> "Unit":
        powers = Counter(dict(self.powers))
        for label, exponent in other.powers:
            powers[label] += sign * exponent
        return Unit(tuple(sorted((label, exponent) for label, exponent in powers.items() if exponent)))

    def label(self, dimensionless: str = "risk units") -> str:
        def side(sign: int) -> str:
            return "·".join(label if abs(power) == 1 else f"{label}^{abs(power)}"
                for label, power in self.powers if power * sign > 0)
        numerator, denominator = side(1), side(-1)
        if not self.powers:
            return dimensionless
        return (numerator or "1") + (f"/({denominator})" if "·" in denominator else f"/{denominator}" if denominator else "")


def transformed_unit(numerator: str, target: str, reference: str, method: str) -> Unit:
    result = Unit.supplied(numerator)
    if method == "none":
        return result
    if method == "beta":
        return result.combine(Unit.supplied(reference)).combine(Unit.supplied(target), -1)
    if target != reference:
        raise ValueError("Volatility and downside normalization require matching target/reference estimation units; choose percentage changes or a compatible reference")
    return result.combine(Unit.supplied(reference), -1)
