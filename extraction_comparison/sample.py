import math
import random
from typing import TypeVar

T = TypeVar("T")


def sample_agreements(items: list[T], rate: float, seed: int) -> list[T]:
    """Pick a random fraction of fully-agreeing records for manual spot-checking.

    Uses a fixed seed so re-runs over the same input pick the same records.
    """
    if rate <= 0 or not items:
        return []
    n = max(1, math.ceil(len(items) * rate))
    n = min(n, len(items))
    rng = random.Random(seed)
    return rng.sample(items, n)
