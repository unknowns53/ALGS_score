"""Abstract base for tournament formats and shared result dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from config import SimulationConfig
from match_sim import MatchResult
from teams import Team


@dataclass
class FormatResult:
    """Unified tournament result across all formats.

    Common fields are populated by every format. Format-specific telemetry
    (e.g. Match Point eligibility timing, double-elim bracket stage counts)
    goes into `extras` so the summary layer can stay format-agnostic.
    """

    format_name: str
    ended: bool
    ending_match: int                       # total matches actually played
    champion_team_id: int | None
    champion_seed: int | None
    teams: list[Team]
    cumulative_scores: np.ndarray           # final per-team total score
    match_results: list[MatchResult]
    # Per-match snapshot of "team that led at match start" — 1-position
    # leader. Used for lead-change counting in format comparison. The first
    # entry is the leader before match 1 (typically tied; we record the
    # lowest team_id among the maxima).
    leader_history: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def number_of_matches(self) -> int:
        return len(self.match_results)


class TournamentFormat(ABC):
    """Pluggable tournament driver.

    A format owns:
      * how teams are partitioned into lobbies per match,
      * how many matches / rounds / brackets to run,
      * when to stop and how to crown the champion.

    Implementations must be picklable so the multiprocessing driver can
    ship them to worker processes — keep state as plain dataclass fields
    or constants, no closures or unpicklable handles.
    """

    name: str = "abstract"

    @abstractmethod
    def simulate(
        self, cfg: SimulationConfig, rng: np.random.Generator
    ) -> FormatResult:
        """Run one full tournament and return the unified result."""

    def __repr__(self) -> str:  # pragma: no cover — trivial
        return f"{type(self).__name__}(name={self.name!r})"


def compute_leader(cumulative: np.ndarray) -> int:
    """Return the lowest-id team currently tied for the lead.

    Deterministic tie-breaker so reproducibility across formats is clean.
    """
    if cumulative.size == 0:
        return -1
    top = int(cumulative.max())
    return int(np.flatnonzero(cumulative == top)[0])
