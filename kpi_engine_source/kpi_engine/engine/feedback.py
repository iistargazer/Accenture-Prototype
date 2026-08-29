"""
Feedback capture + a naive learning loop: repeated 'false alarm' feedback
on a KPI nudges its materiality threshold up. This is intentionally simple
for a prototype - the point is to demonstrate the LOOP (capture -> adjust
-> re-run), not to build a bandit algorithm in a hackathon weekend.
"""
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "output" / "feedback.db"


def _conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kpi TEXT, period TEXT, persona TEXT, rating TEXT, comment TEXT, ts REAL
    )""")
    return conn


def record_feedback(kpi: str, period: str, persona: str, rating: str, comment: str = ""):
    conn = _conn()
    conn.execute(
        "INSERT INTO feedback (kpi, period, persona, rating, comment, ts) VALUES (?,?,?,?,?,?)",
        (kpi, period, persona, rating, comment, time.time()),
    )
    conn.commit()
    conn.close()


def false_alarm_count(kpi: str) -> int:
    conn = _conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM feedback WHERE kpi=? AND rating='false_alarm'", (kpi,)
    ).fetchone()[0]
    conn.close()
    return n


def suggested_threshold_adjustment(kpi: str, current_threshold: float) -> tuple[float, str]:
    """If analysts have repeatedly flagged this KPI's alerts as false alarms,
    suggest raising the materiality bar. Purely additive - never auto-applied
    without a human seeing the suggestion (kept as a suggestion, not a write,
    for prototype safety)."""
    n = false_alarm_count(kpi)
    if n >= 2:
        new_threshold = round(current_threshold * 1.25, 1)
        return new_threshold, f"{n} false-alarm reports on {kpi} - suggest raising threshold {current_threshold}% -> {new_threshold}%"
    return current_threshold, "no adjustment suggested"
