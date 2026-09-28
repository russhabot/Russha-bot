"""ابزارهای ظاهر پیام‌ها (HTML تلگرام). همه‌ی متن‌های ورودی کاربر باید با esc() امن شوند."""
import html

from utils import fmt_num

LINE = "━━━━━━━━━━━━━━"


def esc(v) -> str:
    return html.escape(str(v), quote=False)


def head(emoji: str, text: str) -> str:
    """تیتر بولد + خط جداکننده"""
    return f"{emoji} <b>{esc(text)}</b>\n{LINE}"


def coins(n: int) -> str:
    return f"<b>{fmt_num(n)}</b> 🪙"


def bar(part: int, total: int, width: int = 10) -> str:
    n = 0 if total <= 0 else max(0, min(width, round(width * part / total)))
    return "▓" * n + "░" * (width - n)


def receipt(emoji: str, title: str, *lines: str) -> str:
    return "\n".join([head(emoji, title), *lines])
