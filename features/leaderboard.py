from router import Ctx, callback, kb, text_command
from ui import LINE, coins, esc, head

MEDALS = ["🥇", "🥈", "🥉"]


def _name(r) -> str:
    n = r["full_name"] or (f"@{r['username']}" if r["username"] else str(r["user_id"]))
    return n if len(n) <= 25 else n[:24] + "…"


def _render(db, chat_id, scope: str) -> str:
    rows = db.leaderboard(chat_id if scope == "g" else None, 10)
    title = "🏠" if scope == "g" else "🌍"
    heading = head(title, "برترین روس‌های این گروه" if scope == "g" else "برترین روس‌های جهان")
    if not rows:
        return f"{heading}\n\n😴 هنوز کسی توی جدول نیست!"
    lines = [heading]
    for i, r in enumerate(rows):
        rank = MEDALS[i] if i < 3 else f"<b>{i + 1}.</b>"
        lines.append(f"{rank} <b>{esc(_name(r))}</b> — {coins(r['net'])}")
    lines += [LINE, "💎 <i>بر اساس دارایی کل</i>"]
    return "\n".join(lines)


def _switch_markup(scope: str):
    return kb([[("🌍 جهانی", "lb:w")] if scope == "g" else [("🏠 این گروه", "lb:g")]])


@text_command(r"برترین روس(?: ها)?")
async def ask(c: Ctx) -> None:
    await c.reply(
        "🏆 <b>کدوم جدول رو می‌خوای؟</b>",
        reply_markup=kb([[("🏠 این گروه", "lb:g"), ("🌍 جهانی", "lb:w")]]),
    )


@callback("lb")
async def chosen(c: Ctx) -> None:
    scope = c.args[0] if c.args and c.args[0] in ("g", "w") else "w"
    await c.edit(_render(c.db, c.chat.id, scope), _switch_markup(scope))
