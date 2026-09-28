"""لایه‌ی دیتابیس (SQLite) + قوانین بازی که باید اتمیک باشند.

آپدیت ساختار دیتابیس: یک آیتم جدید به آخر MIGRATIONS اضافه کنید. نسخه با
PRAGMA user_version نگه داشته می‌شود و هنگام اجرای ربات مایگریشن‌های جدید
خودکار اعمال می‌شوند؛ داده‌های قبلی حفظ می‌شوند.
"""
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import date
from typing import Optional

import config
import game
from errors import GameError
from utils import fmt_num

MIGRATIONS: list[list[str]] = [
    # v1: نسخه‌ی اول ربات (کوین جدا برای هر گروه)
    [
        """CREATE TABLE users (
            chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            username TEXT, full_name TEXT,
            coins INTEGER NOT NULL DEFAULT 0,
            privet_count INTEGER NOT NULL DEFAULT 0,
            last_privet_at INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (chat_id, user_id))""",
        "CREATE INDEX idx_users_chat_coins ON users (chat_id, coins DESC)",
    ],
    # v2: حساب جهانی برای هر کاربر + عضویت در گروه‌ها (داده‌های قبلی منتقل می‌شوند)
    [
        """CREATE TABLE players (
            user_id INTEGER PRIMARY KEY,
            username TEXT, full_name TEXT,
            coins INTEGER NOT NULL DEFAULT 0,
            privet_count INTEGER NOT NULL DEFAULT 0,
            last_privet_at INTEGER NOT NULL DEFAULT 0,
            bank_open INTEGER NOT NULL DEFAULT 0,
            bank_balance INTEGER NOT NULL DEFAULT 0,
            invested INTEGER NOT NULL DEFAULT 0,
            debt INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL DEFAULT 0)""",
        """INSERT INTO players (user_id, username, full_name, coins, privet_count, last_privet_at)
           SELECT user_id, MAX(username), MAX(full_name), SUM(coins), SUM(privet_count), MAX(last_privet_at)
           FROM users GROUP BY user_id""",
        """CREATE TABLE group_members (
            chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            PRIMARY KEY (chat_id, user_id))""",
        "INSERT INTO group_members (chat_id, user_id) SELECT chat_id, user_id FROM users",
        "DROP TABLE users",
        "CREATE INDEX idx_players_username ON players (username COLLATE NOCASE)",
    ],
    # v3: ودکا ساز + جدول تنظیمات داخلی
    [
        """CREATE TABLE machines (
            user_id INTEGER PRIMARY KEY,
            level INTEGER NOT NULL DEFAULT 1,
            last_collect_at INTEGER NOT NULL)""",
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    ],
    # v4 به بعد: مثلاً
    # ["ALTER TABLE players ADD COLUMN some_new_column INTEGER NOT NULL DEFAULT 0"],
]

_NET = "(p.coins + p.bank_balance + p.invested - p.debt)"


# ---------------- توابع کمکی داخلی ----------------
def _player(c, user_id: int):
    row = c.execute("SELECT * FROM players WHERE user_id=?", (user_id,)).fetchone()
    if row is None:
        raise GameError("کاربر پیدا نشد. یه بار «پریویت» بنویس تا ثبت‌نام شی.")
    return row


def _bank_player(c, user_id: int):
    row = _player(c, user_id)
    if not row["bank_open"]:
        raise GameError("🏦 اول باید بانک تاسیس کنی! بنویس: بانک روسی")
    return row


def _machine(c, user_id: int):
    row = c.execute("SELECT * FROM machines WHERE user_id=?", (user_id,)).fetchone()
    if row is None:
        raise GameError("🍶 ودکا ساز نداری! بنویس: ودکا ساز")
    return row


def _amount(amount: Optional[int], available: int, label: str) -> int:
    """amount=None یعنی «همه»"""
    if amount is None:
        if available <= 0:
            raise GameError(f"{label} خالیه!")
        return available
    if amount <= 0:
        raise GameError("مبلغ باید بیشتر از صفر باشه.")
    if amount > available:
        raise GameError(f"موجودی {label} کافی نیست. داری: {fmt_num(available)} 🪙")
    return amount


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        for i in range(version, len(MIGRATIONS)):
            self.conn.execute("BEGIN")
            try:
                for stmt in MIGRATIONS[i]:
                    self.conn.execute(stmt)
                self.conn.execute(f"PRAGMA user_version = {i + 1}")
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    @contextmanager
    def tx(self):
        """تراکنش اتمیک؛ هر خطا (از جمله GameError) باعث برگشت کامل تغییرات می‌شود."""
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            else:
                self.conn.execute("COMMIT")

    # ---------------- بازیکنان ----------------
    def touch(self, user_id: int, username: Optional[str], full_name: str, chat_id: Optional[int] = None) -> None:
        """ثبت/به‌روزرسانی بازیکن و (اگر در گروه است) عضویتش در آن گروه"""
        with self.tx() as c:
            c.execute(
                "INSERT INTO players (user_id, username, full_name, created_at) VALUES (?,?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name",
                (user_id, username, full_name, int(time.time())),
            )
            if chat_id is not None:
                c.execute("INSERT OR IGNORE INTO group_members (chat_id, user_id) VALUES (?,?)", (chat_id, user_id))

    def get_player(self, user_id: int):
        with self.lock:
            return self.conn.execute("SELECT * FROM players WHERE user_id=?", (user_id,)).fetchone()

    def get_player_by_username(self, username: str):
        with self.lock:
            return self.conn.execute(
                "SELECT * FROM players WHERE username = ? COLLATE NOCASE", (username,)
            ).fetchone()

    def leaderboard(self, chat_id: Optional[int] = None, limit: int = 10):
        """رتبه‌بندی بر اساس دارایی کل (کیف پول + بانک + سرمایه‌گذاری − بدهی)"""
        with self.lock:
            if chat_id is None:
                return self.conn.execute(
                    f"SELECT p.user_id, p.username, p.full_name, {_NET} AS net FROM players p "
                    f"WHERE {_NET} > 0 ORDER BY net DESC, p.user_id LIMIT ?", (limit,)
                ).fetchall()
            return self.conn.execute(
                f"SELECT p.user_id, p.username, p.full_name, {_NET} AS net FROM players p "
                f"JOIN group_members g ON g.user_id = p.user_id "
                f"WHERE g.chat_id = ? AND {_NET} > 0 ORDER BY net DESC, p.user_id LIMIT ?", (chat_id, limit)
            ).fetchall()

    # ---------------- پریویت ----------------
    def claim_privet(self, user_id: int, now: int, cooldown: int, reward: int):
        """خروجی: (موفق؟، کیف پول، ثانیه‌ی باقی‌مانده)"""
        with self.tx() as c:
            p = _player(c, user_id)
            remaining = p["last_privet_at"] + cooldown - now
            if remaining > 0:
                return False, p["coins"], remaining
            coins = p["coins"] + reward
            c.execute(
                "UPDATE players SET coins=?, privet_count=privet_count+1, last_privet_at=? WHERE user_id=?",
                (coins, now, user_id),
            )
            return True, coins, 0

    # ---------------- بانک ----------------
    def open_bank(self, user_id: int, cost: int) -> None:
        with self.tx() as c:
            p = _player(c, user_id)
            if p["bank_open"]:
                raise GameError("🏦 تو که بانک داری!")
            if p["coins"] < cost:
                raise GameError(
                    f"برای تاسیس بانک {fmt_num(cost)} 🪙 لازمه؛ کیف پولت {fmt_num(p['coins'])} 🪙 داره."
                )
            c.execute("UPDATE players SET coins=coins-?, bank_open=1 WHERE user_id=?", (cost, user_id))

    def deposit(self, user_id: int, amount: Optional[int]):
        """کیف پول ← بانک. خروجی: (مبلغ، موجودی جدید بانک)"""
        with self.tx() as c:
            p = _bank_player(c, user_id)
            amt = _amount(amount, p["coins"], "کیف پول")
            c.execute("UPDATE players SET coins=coins-?, bank_balance=bank_balance+? WHERE user_id=?",
                      (amt, amt, user_id))
            return amt, p["bank_balance"] + amt

    def withdraw(self, user_id: int, amount: Optional[int]):
        """بانک ← کیف پول. خروجی: (مبلغ، کیف پول جدید)"""
        with self.tx() as c:
            p = _bank_player(c, user_id)
            amt = _amount(amount, p["bank_balance"], "حساب بانکی")
            c.execute("UPDATE players SET coins=coins+?, bank_balance=bank_balance-? WHERE user_id=?",
                      (amt, amt, user_id))
            return amt, p["coins"] + amt

    def transfer(self, from_id: int, to_id: int, amount: Optional[int]):
        """حساب بانکی فرستنده ← کیف پول گیرنده. خروجی: (مبلغ، موجودی جدید بانک فرستنده)"""
        if from_id == to_id:
            raise GameError("نمی‌تونی به خودت انتقال بدی 😄")
        with self.tx() as c:
            p = _bank_player(c, from_id)
            amt = _amount(amount, p["bank_balance"], "حساب بانکی")
            if c.execute("SELECT 1 FROM players WHERE user_id=?", (to_id,)).fetchone() is None:
                raise GameError("این کاربر هنوز توی ربات ثبت نشده.")
            c.execute("UPDATE players SET bank_balance=bank_balance-? WHERE user_id=?", (amt, from_id))
            c.execute("UPDATE players SET coins=coins+? WHERE user_id=?", (amt, to_id))
            return amt, p["bank_balance"] - amt

    def invest(self, user_id: int, amount: Optional[int]):
        """بانک ← سرمایه‌گذاری. خروجی: (مبلغ، کل سرمایه)"""
        with self.tx() as c:
            p = _bank_player(c, user_id)
            amt = _amount(amount, p["bank_balance"], "حساب بانکی")
            if amt < config.MIN_INVEST:
                raise GameError(f"حداقل مبلغ سرمایه‌گذاری {fmt_num(config.MIN_INVEST)} 🪙 هست.")
            c.execute("UPDATE players SET bank_balance=bank_balance-?, invested=invested+? WHERE user_id=?",
                      (amt, amt, user_id))
            return amt, p["invested"] + amt

    def divest(self, user_id: int, amount: Optional[int]):
        """سرمایه‌گذاری ← بانک. خروجی: (مبلغ، کل سرمایه‌ی باقی‌مانده)"""
        with self.tx() as c:
            p = _bank_player(c, user_id)
            amt = _amount(amount, p["invested"], "سرمایه‌گذاری")
            c.execute("UPDATE players SET bank_balance=bank_balance+?, invested=invested-? WHERE user_id=?",
                      (amt, amt, user_id))
            return amt, p["invested"] - amt

    def borrow(self, user_id: int, amount: Optional[int]):
        """وام به حساب بانکی. خروجی: (مبلغ، بدهی جدید، موجودی جدید بانک)"""
        if amount is None or amount <= 0:
            raise GameError("مبلغ وام رو مشخص کن. مثال: وام 500")
        with self.tx() as c:
            p = _bank_player(c, user_id)
            add = game.loan_debt_for(amount)
            if p["debt"] + add > config.MAX_DEBT:
                raise GameError(
                    f"سقف بدهی {fmt_num(config.MAX_DEBT)} 🪙 هست. "
                    f"الان حداکثر می‌تونی {fmt_num(game.max_borrowable(p['debt']))} 🪙 وام بگیری."
                )
            c.execute("UPDATE players SET bank_balance=bank_balance+?, debt=debt+? WHERE user_id=?",
                      (amount, add, user_id))
            return amount, p["debt"] + add, p["bank_balance"] + amount

    def repay(self, user_id: int, amount: Optional[int]):
        """پرداخت بدهی از حساب بانکی. خروجی: (مبلغ پرداختی، بدهی باقی‌مانده)"""
        with self.tx() as c:
            p = _bank_player(c, user_id)
            if p["debt"] <= 0:
                raise GameError("✅ بدهی نداری!")
            if amount is None:
                amt = min(p["debt"], p["bank_balance"])
                if amt <= 0:
                    raise GameError("حساب بانکی‌ت خالیه؛ اول پول واریز کن.")
            else:
                amt = _amount(min(amount, p["debt"]), p["bank_balance"], "حساب بانکی")
            c.execute("UPDATE players SET bank_balance=bank_balance-?, debt=debt-? WHERE user_id=?",
                      (amt, amt, user_id))
            return amt, p["debt"] - amt

    def run_nightly(self, today: date) -> int:
        """سود سرمایه‌گذاری و بهره‌ی وام. اگر ربات چند شب خاموش بوده، جبران می‌شود.
        خروجی: تعداد شب‌هایی که اعمال شد."""
        with self.tx() as c:
            row = c.execute("SELECT value FROM meta WHERE key='nightly_last'").fetchone()
            upsert = ("INSERT INTO meta (key, value) VALUES ('nightly_last', ?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value")
            if row is None:
                c.execute(upsert, (today.isoformat(),))
                return 0
            elapsed = (today - date.fromisoformat(row["value"])).days
            if elapsed <= 0:
                return 0
            days = min(elapsed, config.MAX_CATCHUP_DAYS)
            c.execute(
                "UPDATE players SET "
                "bank_balance = bank_balance + invested * ? / 100, "
                "debt = debt + debt * ? / 100 "
                "WHERE bank_open = 1",
                (config.INVEST_DAILY_PERCENT * days, config.LOAN_DAILY_PERCENT * days),
            )
            c.execute(upsert, (today.isoformat(),))
            return days

    # ---------------- ودکا ساز ----------------
    def get_machine(self, user_id: int):
        with self.lock:
            return self.conn.execute("SELECT * FROM machines WHERE user_id=?", (user_id,)).fetchone()

    def buy_machine(self, user_id: int, price: int, now: Optional[int] = None) -> None:
        now = int(time.time()) if now is None else now
        with self.tx() as c:
            p = _player(c, user_id)
            if c.execute("SELECT 1 FROM machines WHERE user_id=?", (user_id,)).fetchone():
                raise GameError("🍶 تو که ودکا ساز داری!")
            if p["coins"] < price:
                raise GameError(f"قیمت ودکا ساز {fmt_num(price)} 🪙 هست؛ کیف پولت {fmt_num(p['coins'])} 🪙 داره.")
            c.execute("UPDATE players SET coins=coins-? WHERE user_id=?", (price, user_id))
            c.execute("INSERT INTO machines (user_id, level, last_collect_at) VALUES (?,1,?)", (user_id, now))

    def collect_machine(self, user_id: int, now: Optional[int] = None) -> int:
        now = int(time.time()) if now is None else now
        with self.tx() as c:
            m = _machine(c, user_id)
            got = game.machine_pending(m["level"], now - m["last_collect_at"])
            if got < 1:
                raise GameError("هنوز چیزی تولید نشده، کمی صبر کن ⏳")
            c.execute("UPDATE players SET coins=coins+? WHERE user_id=?", (got, user_id))
            c.execute("UPDATE machines SET last_collect_at=? WHERE user_id=?", (now, user_id))
            return got

    def upgrade_machine(self, user_id: int, now: Optional[int] = None):
        """خروجی: (سطح جدید، هزینه، مقدار برداشت‌شده‌ی خودکار). تولید معوقه پیش از ارتقا به کیف پول می‌رود."""
        now = int(time.time()) if now is None else now
        with self.tx() as c:
            m = _machine(c, user_id)
            p = _player(c, user_id)
            if m["level"] >= config.VODKA_MAX_LEVEL:
                raise GameError("🔝 ودکا ساز به بالاترین سطح رسیده.")
            pending = game.machine_pending(m["level"], now - m["last_collect_at"])
            cost = game.machine_upgrade_cost(m["level"])
            if p["coins"] + pending < cost:
                raise GameError(f"ارتقا {fmt_num(cost)} 🪙 هزینه داره؛ کیف پولت {fmt_num(p['coins'])} 🪙 داره.")
            c.execute("UPDATE players SET coins=coins+?-? WHERE user_id=?", (pending, cost, user_id))
            c.execute("UPDATE machines SET level=level+1, last_collect_at=? WHERE user_id=?", (now, user_id))
            return m["level"] + 1, cost, pending
