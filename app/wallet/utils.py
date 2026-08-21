def to_cent(amount: float) -> int:
    return int(round(amount * 100))


def from_cent(cents: int) -> float:
    return cents / 100
