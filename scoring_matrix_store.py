import sqlite3
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS scoring_matrix (
    state  TEXT NOT NULL,
    action TEXT NOT NULL,
    value  REAL NOT NULL,
    PRIMARY KEY (state, action)
);
"""

SELECT_SCORE = "SELECT state, action, value FROM scoring_matrix"

DELETE_SCORE = "DELETE FROM scoring_matrix"

INSERT_SCORE = "INSERT INTO scoring_matrix (state, action, value) VALUES (?, ?, ?)"


class ScoringMatrixStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.executescript(DDL)
        self._conn.commit()

    def load(self) -> dict[str, dict[str, float]]:
        table: dict[str, dict[str, float]] = {}

        for state, action, value in self._conn.execute(SELECT_SCORE):
            table.setdefault(state, {})[action] = value

        return table

    def save(self, table: dict[str, dict[str, float]]) -> None:
        rows = [
            (state, action, value)
            for state, actions in table.items()
            for action, value in actions.items()
        ]
        self._conn.execute(DELETE_SCORE)
        self._conn.executemany(INSERT_SCORE, rows)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
