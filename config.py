"""همه‌ی تنظیمات قابل تغییر ربات. مقدارها از فایل .env خوانده می‌شوند."""
import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_PATH = os.getenv("DB_PATH", "rasha_bot.sqlite3")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tehran")

# ---- پریویت ----
PRIVET_TRIGGERS = [t.strip() for t in os.getenv("TRIGGERS", "پریویت,привет").split(",") if t.strip()]
COOLDOWN_SECONDS = _int("COOLDOWN_SECONDS", 300)
REWARD_MIN = _int("REWARD_MIN", 1)
REWARD_MAX = _int("REWARD_MAX", 5)

# ---- بانک ----
BANK_FOUNDING_COST = _int("BANK_FOUNDING_COST", 500)
INVEST_DAILY_PERCENT = _int("INVEST_DAILY_PERCENT", 2)   # سود سرمایه‌گذاری هر شب
MIN_INVEST = _int("MIN_INVEST", 100)
LOAN_FEE_PERCENT = _int("LOAN_FEE_PERCENT", 5)           # کارمزد یک‌باره‌ی وام
LOAN_DAILY_PERCENT = _int("LOAN_DAILY_PERCENT", 3)       # بهره‌ی شبانه‌ی بدهی
MAX_DEBT = _int("MAX_DEBT", 3000)
MAX_CATCHUP_DAYS = 7  # اگر ربات چند شب خاموش بود، حداکثر برای چند شب سود/بهره حساب شود

# نکته: بهره‌ی وام عمداً بیشتر از سود سرمایه‌گذاری است تا «وام بگیر و سرمایه‌گذاری کن» پول‌ساز نشود.

# ---- ودکا ساز ----
VODKA_PRICE = _int("VODKA_PRICE", 5000)
VODKA_BASE_RATE = _int("VODKA_BASE_RATE", 2)             # راشا کوین در ثانیه (سطح ۱)
VODKA_BASE_CAPACITY = _int("VODKA_BASE_CAPACITY", 3600)  # ظرفیت (سطح ۱)
VODKA_MAX_LEVEL = _int("VODKA_MAX_LEVEL", 10)
VODKA_UPGRADE_BASE_COST = _int("VODKA_UPGRADE_BASE_COST", 5000)
