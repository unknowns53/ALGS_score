"""Tournament format strategies.

Each format encapsulates its own match-driving logic, lobby composition,
and termination condition. The shared interface lives in `formats.base`.
"""

from formats.base import FormatResult, TournamentFormat
from formats.double_elim import DoubleEliminationFormat
from formats.fixed_matches import FixedMatchesFormat
from formats.match_point import MatchPointFormat
from formats.round_robin import RoundRobinFormat
from formats.swiss import SwissFormat

__all__ = [
    "FormatResult",
    "TournamentFormat",
    "MatchPointFormat",
    "FixedMatchesFormat",
    "SwissFormat",
    "RoundRobinFormat",
    "DoubleEliminationFormat",
]
