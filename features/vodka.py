import time

import config
import game
from router import Ctx, callback, kb, text_command
from ui import LINE, bar, coins, head, receipt
from utils import fmt_duration, fmt_num


async def _show(c: Ctx, edit: bool = False) -> None:
    uid = c.user.id
    m = c.db.get_machine(uid)
    p = c.db.get_player(uid)

    if m is None:
        text = (
            f"{head('🍶', 'ودکا ساز')}\n"
            "یه دستگاه شخصی که حتی وقتی آفلاینی برات راشا کوین تولید می‌کنه! 😎\n\n"
            f"⚙️ تولید: <b>{fmt_num(game.machine_rate(1))}</b> 🪙 در ثانیه\n"
            f"📦 ظرفیت: {coins(game.machine_capacity(1))} <i>(باید برداشت کنی تا دوباره پر بشه)</i>\n"
            f"💰 قیمت: {coins(config.VODKA_PRICE)}\n"
            f"{LINE}\n"
            f"💵 کیف پولت: {coins(p['coins'])}"
        )
        markup = kb([[(f"🛒 خرید ({fmt_num(config.VODKA_PRICE)} 🪙)", f"vodka:buy:{uid}")]])
    else:
        lvl = m["level"]
        rate, cap = game.machine_rate(lvl), game.machine_capacity(lvl)
        pend = game.machine_pending(lvl, int(time.time()) - m["last_collect_at"])
        state = ("🔴 <b>پُره!</b> برداشت کن تا دوباره تولید کنه" if pend >= cap
                 else f"⏱ تا پر شدن: <b>{fmt_duration((cap - pend) / rate)}</b>")
        text = (
            f"{head('🍶', f'ودکا ساز — سطح {lvl}/{config.VODKA_MAX_LEVEL}')}\n"
            f"⚙️ تولید: <b>{fmt_num(rate)}</b> 🪙 در ثانیه\n"
            f"📦 {bar(pend, cap)}\n"
            f"     <code>{fmt_num(pend)} / {fmt_num(cap)}</code>\n"
            f"{state}\n"
            f"{LINE}\n"
            f"💵 کیف پولت: {coins(p['coins'])}"
        )
        rows = [[("📥 برداشت", f"vodka:collect:{uid}")]]
        if lvl < config.VODKA_MAX_LEVEL:
            rows.append([(f"⬆️ ارتقا به سطح {lvl + 1} ({fmt_num(game.machine_upgrade_cost(lvl))} 🪙)", f"vodka:upgrade:{uid}")])
        rows.append([("🔄 بروزرسانی", f"vodka:menu:{uid}")])
        markup = kb(rows)

    if edit:
        await c.edit(text, markup)
    else:
        await c.reply(text, reply_markup=markup)


@text_command(r"ودکا ?ساز")
async def menu(c: Ctx) -> None:
    await _show(c)


@callback("vodka")
async def buttons(c: Ctx) -> None:
    c.require_owner()
    action, uid = c.args[0], c.user.id
    if action == "buy":
        c.db.buy_machine(uid, config.VODKA_PRICE)
        await c.answer("🎉 ودکا ساز خریداری شد!")
    elif action == "collect":
        got = c.db.collect_machine(uid)
        await c.answer(f"🍶 {fmt_num(got)} 🪙 برداشت شد")
    elif action == "upgrade":
        lvl, _, _ = c.db.upgrade_machine(uid)
        await c.answer(f"⬆️ ارتقا یافت! سطح {lvl}")
    await _show(c, edit=True)


@text_command(r"خرید ودکا ?ساز")
async def buy(c: Ctx) -> None:
    c.db.buy_machine(c.user.id, config.VODKA_PRICE)
    await c.reply(receipt("🎉", "ودکا ساز خریداری شد!", "🍶 برای دیدن وضعیتش بنویس: <b>ودکا ساز</b>"))


@text_command(r"برداشت ودکا")
async def collect(c: Ctx) -> None:
    got = c.db.collect_machine(c.user.id)
    p = c.db.get_player(c.user.id)
    await c.reply(receipt("🍶", "برداشت شد", f"📥 مقدار: {coins(got)}", f"💰 کیف پول: {coins(p['coins'])}"))


@text_command(r"ارتقا[ءی]? ودکا ?ساز")
async def upgrade(c: Ctx) -> None:
    lvl, cost, pending = c.db.upgrade_machine(c.user.id)
    lines = [f"🏷 هزینه: {coins(cost)}", f"🆙 سطح جدید: <b>{lvl}</b>"]
    if pending:
        lines.append(f"📥 تولید معوقه‌ی {coins(pending)} هم به کیف پولت اضافه شد")
    await c.reply(receipt("⬆️", "ودکا ساز ارتقا یافت!", *lines))
