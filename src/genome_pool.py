"""
Persistent genome pool backed by SQLite.

Survives across simulations so each new run can seed from the fittest
genomes produced by all previous runs.
"""

import random
import sqlite3
from pathlib import Path

import config as _cfg
from genome import GENE_DEFAULTS, clamp_genome

_DDL = """
CREATE TABLE IF NOT EXISTS genome_pool (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_id           TEXT    NOT NULL,
    agent_id         TEXT    NOT NULL,
    born_tick        INTEGER NOT NULL,
    died_tick        INTEGER NOT NULL,
    lifespan         INTEGER NOT NULL,
    offspring        INTEGER NOT NULL DEFAULT 0,
    fitness          REAL    NOT NULL,
    idle_threshold   REAL    NOT NULL,
    breakaway_margin REAL    NOT NULL,
    metabolism       REAL    NOT NULL,
    water_drain_rate REAL    NOT NULL,
    rest_drain_rate  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fitness ON genome_pool (fitness DESC);
"""

_INSERT = """
INSERT INTO genome_pool
    (sim_id, agent_id, born_tick, died_tick, lifespan, offspring, fitness,
     idle_threshold, breakaway_margin, metabolism, water_drain_rate, rest_drain_rate)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_GENE_COLUMNS = (
    "idle_threshold",
    "breakaway_margin",
    "metabolism",
    "water_drain_rate",
    "rest_drain_rate",
)


class GenomePool:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.executescript(_DDL)
        self._conn.commit()

    # ------------------------------------------------------------------

    def record(self, agent, sim_id: str, died_tick: int) -> None:
        """Write one death record.  Call before agent.die()."""
        g = agent.behavioral_genome
        lifespan = agent.age
        fitness = lifespan * (1.0 + agent.offspring_count * _cfg.OFFSPRING_WEIGHT)
        self._conn.execute(
            _INSERT,
            (
                sim_id,
                str(agent.id),
                agent.birth_tick,
                died_tick,
                lifespan,
                agent.offspring_count,
                fitness,
                g["idle_threshold"],
                g["breakaway_margin"],
                g["metabolism"],
                g["water_drain_rate"],
                g["rest_drain_rate"],
            ),
        )
        self._conn.commit()

    def sample_elite(self, n: int) -> list[dict[str, float]]:
        """Return n genomes sampled uniformly from the top-20% by fitness."""
        total = self.size()
        elite_count = max(1, total // 5)
        rows = self._conn.execute(
            f"SELECT {', '.join(_GENE_COLUMNS)} "
            "FROM genome_pool ORDER BY fitness DESC LIMIT ?",
            (elite_count,),
        ).fetchall()

        result: list[dict[str, float]] = []
        for _ in range(n):
            row = random.choice(rows)
            genome = dict(zip(_GENE_COLUMNS, row))
            result.append(clamp_genome(genome))
        return result

    def size(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM genome_pool").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
