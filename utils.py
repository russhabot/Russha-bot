import re

from errors import GameError

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize(text: str) -> str:
    """یکسان‌سازی متن: ارقام فارسی/عربی، ی/ک عربی، نیم‌فاصله، حروف کوچک، فاصله‌ها."""
    t = text.translate(_DIGITS)
    t = t.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    t = t.replace("\u200c", " ").replace("\u200f", "").replace("\u200e", "")
    return re.sub(r"\s+", " ", t.lower()).strip()


def fmt_num(n: int) -> str:
    return f"{int(n):,}"


def fmt_duration(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h} ساعت")
    if m:
        parts.append(f"{m} دقیقه")
    if s or not parts:
        parts.append(f"{s} ثانیه")
    return " و ".join(parts)


def parse_amount(raw: str):
    """عدد یا «همه». برای «همه» مقدار None برمی‌گرداند."""
    raw = raw.strip()
    if raw in ("همه", "all"):
        return None
    digits = re.sub(r"[,٬،]", "", raw)
    if not digits.isdigit() or len(digits) > 12:
        raise GameError("مبلغ نامعتبره. یه عدد بنویس یا «همه».")
    return int(digits)
