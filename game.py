"""فرمول‌های بازی. برای بالانس اقتصاد فقط همین‌جا (یا .env) را عوض کنید."""
import config


# ---- ودکا ساز ----
def machine_rate(level: int) -> int:
    """راشا کوین در ثانیه"""
    return config.VODKA_BASE_RATE * level


def machine_capacity(level: int) -> int:
    return config.VODKA_BASE_CAPACITY * level


def machine_upgrade_cost(level: int) -> int:
    """هزینه‌ی رفتن از سطح `level` به سطح بعد"""
    return config.VODKA_UPGRADE_BASE_COST * level


def machine_pending(level: int, elapsed_seconds: float) -> int:
    return min(machine_capacity(level), int(max(elapsed_seconds, 0) * machine_rate(level)))


# ---- بانک ----
def loan_debt_for(amount: int) -> int:
    """بدهی‌ای که با گرفتن `amount` وام ایجاد می‌شود (با کارمزد، رو به بالا)"""
    return -(-amount * (100 + config.LOAN_FEE_PERCENT) // 100)


def max_borrowable(current_debt: int) -> int:
    return max(0, (config.MAX_DEBT - current_debt) * 100 // (100 + config.LOAN_FEE_PERCENT))


def tonight_profit(invested: int) -> int:
    return invested * config.INVEST_DAILY_PERCENT // 100
