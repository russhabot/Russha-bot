import time

import config
import game
from router import Ctx, text_command
from ui import LINE, bar, coins, esc, head
from utils import fmt_duration, fmt_num


@text_command(r"(?:وضعیت|موجودی|کیف پول|static|stats|استاتیک)")
async def status(c: Ctx) -> None:
    now = int(time.time())
    p = c.db.get_player(c.user.id)
    m = c.db.get_machine(c.user.id)

    lines = [head("📊", f"وضعیت {c.user.first_name}"), f"💰 کیف پول: {coins(p['coins'])}"]
    if p["bank_open"]:
        lines.append(f"🏛 حساب بانکی: {coins(p['bank_balance'])}")
        lines.append(f"📈 سرمایه‌گذاری: {coins(p['invested'])}")
        if p["debt"]:
            lines.append(f"💳 بدهی: {coins(p['debt'])}")
    if m:
        lvl = m["level"]
        cap = game.machine_capacity(lvl)
        pend = game.machine_pending(lvl, now - m["last_collect_at"])
        lines.append(f"🍶 ودکا ساز سطح <b>{lvl}</b>\n     {bar(pend, cap)} <code>{fmt_num(pend)}/{fmt_num(cap)}</code>")

    net = p["coins"] + p["bank_balance"] + p["invested"] - p["debt"]
    lines.append(LINE)
    lines.append(f"💎 دارایی کل: {coins(net)}")
    lines.append(f"👋 تعداد پریویت: <b>{p['privet_count']}</b>")
    left = p["last_privet_at"] + config.COOLDOWN_SECONDS - now
    lines.append("✅ <i>الان می‌تونی پریویت بگی</i>" if left <= 0 else f"⏳ <i>{fmt_duration(left)} تا پریویت بعدی</i>")
    await c.reply("\n".join(lines))
