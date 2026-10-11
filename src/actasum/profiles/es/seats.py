"""Seat allocation under the LOREG, to tell whether a difference in votes
would change who gets a seat.

Article 163.1 gives the method (highest quotients of votes divided by 1, 2,
3...). Article 180 applies it to municipal councils with a threshold of 5 per
cent of the valid votes cast in the municipality; valid votes are the votes
for candidatures plus the blank votes.

This is an aid for reading differences. It proclaims nothing: seats are
proclaimed by the electoral boards.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

LOCAL_THRESHOLD_PERCENT = 5


@dataclass(frozen=True)
class Allocation:
    seats: dict[str, int]  # candidature code -> seats, only those with at least one
    # True when the last seat falls on a tie that the law settles by lot: equal
    # quotients between candidatures with the same total votes (art. 163.1.d).
    by_lot: bool = False


def allocate(
    votes: dict[str, int], blank: int, seats: int, threshold_percent: int
) -> Allocation:
    """Distribute ``seats`` among candidatures by highest quotients."""
    if seats <= 0:
        return Allocation({})
    valid = sum(votes.values()) + blank
    eligible = {
        code: count
        for code, count in votes.items()
        if count > 0 and count * 100 >= threshold_percent * valid
    }
    # Equal quotients go to the candidature with more total votes; the code
    # is only there to make the order reproducible.
    quotients = sorted(
        (
            (Fraction(count, divisor), count, code)
            for code, count in eligible.items()
            for divisor in range(1, seats + 1)
        ),
        key=lambda item: (-item[0], -item[1], item[2]),
    )
    won: dict[str, int] = {}
    for _, _, code in quotients[:seats]:
        won[code] = won.get(code, 0) + 1
    by_lot = False
    if len(quotients) > seats:
        last_in, first_out = quotients[seats - 1], quotients[seats]
        by_lot = last_in[:2] == first_out[:2] and last_in[2] != first_out[2]
    return Allocation(won, by_lot)
