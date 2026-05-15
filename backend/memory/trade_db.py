"""
Quorum — Trade Database
SQLite database for trade history, portfolio snapshots, agent accuracy, and analysis logs.
Includes indexes, portfolio state management, performance metrics, and schema migrations.
"""

import aiosqlite
import json
import logging
from datetime import datetime
from typing import Optional
from config import SQLITE_DB_PATH, INITIAL_CAPITAL

logger = logging.getLogger("quorum.db")


class TradeDB:
    """Async SQLite database for trade records and portfolio state."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(SQLITE_DB_PATH)

    async def initialize(self):
        """Create tables, indexes, and run migrations for existing databases."""
        async with aiosqlite.connect(self.db_path) as db:

            # ─── Trades ───────────────────────────────────────
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    price REAL NOT NULL DEFAULT 0,
                    confidence REAL DEFAULT 0,
                    reasoning TEXT DEFAULT '',
                    approval_status TEXT DEFAULT 'pending',
                    pnl REAL,
                    created_at TEXT NOT NULL,
                    executed_at TEXT
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at DESC)"
            )

            # ─── Portfolio Snapshots ───────────────────────────
            await db.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cash REAL NOT NULL DEFAULT 0,
                    equity REAL NOT NULL DEFAULT 0,
                    total_value REAL NOT NULL DEFAULT 0,
                    positions_json TEXT DEFAULT '[]',
                    daily_pnl REAL DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_portfolio_ts ON portfolio_snapshots(timestamp DESC)"
            )

            # ─── Agent Accuracy ───────────────────────────────
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_accuracy (
                    agent_name TEXT PRIMARY KEY,
                    total_predictions INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    accuracy REAL DEFAULT 0.0,
                    weight REAL DEFAULT 1.0,
                    last_updated TEXT
                )
            """)

            # ─── Analysis Logs ────────────────────────────────
            await db.execute("""
                CREATE TABLE IF NOT EXISTS analysis_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    asset_type TEXT DEFAULT 'stock',
                    trade_date TEXT,
                    action TEXT,
                    confidence REAL,
                    trade_approved INTEGER DEFAULT 0,
                    full_state_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_ticker ON analysis_logs(ticker)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_created ON analysis_logs(created_at DESC)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_session ON analysis_logs(session_id)"
            )

            # ─── Migrations ───────────────────────────────────
            # Safely add columns that may be missing in databases created before
            # the current schema. ALTER TABLE ADD COLUMN fails if the column
            # already exists, so we catch and ignore that error.
            _migrations = [
                "ALTER TABLE analysis_logs ADD COLUMN action TEXT",
                "ALTER TABLE analysis_logs ADD COLUMN confidence REAL",
                "ALTER TABLE analysis_logs ADD COLUMN trade_approved INTEGER DEFAULT 0",
                "ALTER TABLE analysis_logs ADD COLUMN session_id TEXT",
            ]
            for sql in _migrations:
                try:
                    await db.execute(sql)
                except Exception:
                    pass  # Column already exists — safe to ignore

            # ─── Seed initial portfolio ───────────────────────
            cursor = await db.execute("SELECT COUNT(*) FROM portfolio_snapshots")
            count = (await cursor.fetchone())[0]
            if count == 0:
                await db.execute(
                    """INSERT INTO portfolio_snapshots
                       (cash, equity, total_value, positions_json, daily_pnl, total_pnl, timestamp)
                       VALUES (?, 0, ?, '[]', 0, 0, ?)""",
                    (INITIAL_CAPITAL, INITIAL_CAPITAL, datetime.utcnow().isoformat()),
                )

            await db.commit()

        logger.info(f"TradeDB initialized at {self.db_path}")

    # ─── Trades ───────────────────────────────────────────────

    async def insert_trade(
        self,
        ticker: str,
        asset_type: str,
        action: str,
        quantity: float,
        price: float,
        confidence: float = 0.0,
        reasoning: str = "",
        approval_status: str = "pending",
    ) -> int:
        """Insert a trade record and return its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO trades
                   (ticker, asset_type, action, quantity, price, confidence,
                    reasoning, approval_status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ticker, asset_type, action,
                    round(quantity, 6), round(price, 6),
                    round(confidence, 4), reasoning[:2000],
                    approval_status, datetime.utcnow().isoformat(),
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_trades(
        self, ticker: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        """Get trade history, newest first."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if ticker:
                cursor = await db.execute(
                    "SELECT * FROM trades WHERE ticker = ? ORDER BY created_at DESC LIMIT ?",
                    (ticker.upper(), limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ─── Portfolio ────────────────────────────────────────────

    async def save_portfolio_snapshot(
        self,
        cash: float,
        equity: float,
        total_value: float,
        positions: list,
        daily_pnl: float,
        total_pnl: float,
    ):
        """Save a portfolio snapshot."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO portfolio_snapshots
                   (cash, equity, total_value, positions_json, daily_pnl, total_pnl, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    round(cash, 2), round(equity, 2), round(total_value, 2),
                    json.dumps(positions, default=str),
                    round(daily_pnl, 2), round(total_pnl, 2),
                    datetime.utcnow().isoformat(),
                ),
            )
            await db.commit()

    async def get_portfolio_history(self, limit: int = 100) -> list[dict]:
        """Get portfolio snapshot history, newest first."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                try:
                    d["positions"] = json.loads(d.get("positions_json") or "[]")
                except Exception:
                    d["positions"] = []
                result.append(d)
            return result

    async def get_current_portfolio(self) -> dict:
        """Get the most recent portfolio snapshot."""
        history = await self.get_portfolio_history(limit=1)
        if history:
            return history[0]
        return {
            "cash": INITIAL_CAPITAL,
            "equity": 0.0,
            "total_value": INITIAL_CAPITAL,
            "positions": [],
            "daily_pnl": 0.0,
            "total_pnl": 0.0,
        }

    # ─── Analysis Logs ────────────────────────────────────────

    async def save_analysis_log(
        self,
        ticker: str,
        asset_type: str,
        trade_date: str,
        state_dict: dict,
        session_id: Optional[str] = None,
    ):
        """Save a full analysis pipeline state."""
        signal = state_dict.get("trade_signal") or {}
        if isinstance(signal, dict):
            action = signal.get("action")
            confidence = signal.get("confidence")
        else:
            action = getattr(signal, "action", None)
            confidence = getattr(signal, "confidence", None)

        trade_approved = int(bool(state_dict.get("trade_approved", False)))

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO analysis_logs
                   (ticker, asset_type, trade_date, action, confidence,
                    trade_approved, full_state_json, session_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ticker.upper(), asset_type, trade_date,
                    str(action) if action else None,
                    float(confidence) if confidence is not None else None,
                    trade_approved,
                    json.dumps(state_dict, default=str),
                    session_id,
                    datetime.utcnow().isoformat(),
                ),
            )
            await db.commit()

    async def get_analysis_logs(
        self, ticker: Optional[str] = None, limit: int = 20
    ) -> list[dict]:
        """Get analysis log summaries (without full state JSON for performance)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if ticker:
                cursor = await db.execute(
                    """SELECT id, ticker, asset_type, trade_date, action, confidence,
                              trade_approved, created_at
                       FROM analysis_logs WHERE ticker = ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (ticker.upper(), limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT id, ticker, asset_type, trade_date, action, confidence,
                              trade_approved, created_at
                       FROM analysis_logs ORDER BY created_at DESC LIMIT ?""",
                    (limit,),
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_analysis_by_session(self, session_id: str) -> Optional[dict]:
        """Get the full analysis state for a given session ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT full_state_json FROM analysis_logs WHERE session_id = ? LIMIT 1",
                (session_id,),
            )
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row["full_state_json"])
                except Exception:
                    return None
            return None

    # ─── Agent Accuracy ───────────────────────────────────────

    async def update_agent_accuracy(
        self,
        agent_name: str,
        total: int,
        correct: int,
        accuracy: float,
        weight: float,
    ):
        """Upsert agent accuracy record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO agent_accuracy
                   (agent_name, total_predictions, correct_predictions, accuracy, weight, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(agent_name) DO UPDATE SET
                     total_predictions = excluded.total_predictions,
                     correct_predictions = excluded.correct_predictions,
                     accuracy = excluded.accuracy,
                     weight = excluded.weight,
                     last_updated = excluded.last_updated""",
                (
                    agent_name, total, correct,
                    round(accuracy, 4), round(weight, 4),
                    datetime.utcnow().isoformat(),
                ),
            )
            await db.commit()

    async def get_agent_accuracy(self) -> list[dict]:
        """Get all agent accuracy records."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM agent_accuracy ORDER BY accuracy DESC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ─── Performance Metrics ──────────────────────────────────

    async def get_performance_metrics(self) -> dict:
        """Calculate aggregate performance metrics from trade history."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT action, pnl, confidence FROM trades WHERE pnl IS NOT NULL"
            )
            trades = [dict(row) for row in await cursor.fetchall()]

        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_trade_pnl": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
            }

        pnls = [t["pnl"] for t in trades if t["pnl"] is not None]
        winning = [p for p in pnls if p > 0]
        losing = [p for p in pnls if p <= 0]

        return {
            "total_trades": len(pnls),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(len(winning) / len(pnls), 4) if pnls else 0.0,
            "total_pnl": round(sum(pnls), 2),
            "avg_trade_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
            "best_trade": round(max(pnls), 2) if pnls else 0.0,
            "worst_trade": round(min(pnls), 2) if pnls else 0.0,
        }
