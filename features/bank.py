import config
import game
from errors import GameError
from router import Ctx, callback, kb, text_command
from ui import LINE, coins, esc, head, receipt
from utils import fmt_num, parse_amount

AMT = r"(?P<amount>[\d,٬،]+|همه|all)"


def _summary(p) -> str:
    net = p["coins"] + p["bank_balance"] + p["invested"] - p["debt"]
    lines = [
        head("🏦", f"بانک روسی — {p['full_name']}"),
        f"💵 کیف پول: {coins(p['coins'])}",
        f"🏛 حساب بانکی: {coins(p['bank_balance'])}",
        f"📈 سرمایه‌گذاری: {coins(p['invested'])} <i>(سود امشب +{fmt_num(game.tonight_profit(p['invested']))})</i>",
    ]
    if p["debt"]:
        lines.append(f"💳 بدهی: {coins(p['debt'])} <i>(بهره‌ی شبانه {config.LOAN_DAILY_PERCENT}٪)</i>")
    lines += [LINE, f"💎 دارایی کل: {coins(net)}"]
    return "\n".join(lines)


def _footer() -> str:
    return (
        "\n\n<blockquote>"
        f"📈 سود سرمایه‌گذاری: <b>{config.INVEST_DAILY_PERCENT}٪</b> هر شب ساعت ۱۲ (تهران)\n"
        f"💳 کارمزد وام: <b>{config.LOAN_FEE_PERCENT}٪</b> · بهره‌ی شبانه: <b>{config.LOAN_DAILY_PERCENT}٪</b>\n"
        f"🚧 سقف بدهی: <b>{fmt_num(config.MAX_DEBT)}</b> 🪙"
        "</blockquote>\n"
        "⌨️ <i>میان‌بُر متنی: واریز 100 ، برداشت 100 ، وام 500 ، انتقال 100 @یوزرنیم</i>"
    )


# کلید -> (عنوان، مقدارِ قابل استفاده، دکمه‌های مبلغ آماده، آیا «همه» مجاز است)
_ACTIONS = {
    "dep": ("💵", "واریز به بانک (کیف پول ← بانک)", "کیف پول", lambda p: p["coins"], (100, 500, 1000, 5000), True),
    "wd": ("🏛", "برداشت از بانک (بانک ← کیف پول)", "حساب بانکی", lambda p: p["bank_balance"], (100, 500, 1000, 5000), True),
    "inv": ("📈", "سرمایه‌گذاری (بانک ← سرمایه)", "حساب بانکی", lambda p: p["bank_balance"], (100, 500, 1000, 5000), True),
    "div": ("📉", "برداشت سرمایه (سرمایه ← بانک)", "سرمایه‌گذاری", lambda p: p["invested"], (100, 500, 1000, 5000), True),
    "loan": ("💳", "گرفتن وام", "سقف وام فعلی", lambda p: game.max_borrowable(p["debt"]), (500, 1000, 2000), False),
    "repay": ("✅", "پرداخت وام", "بدهی", lambda p: p["debt"], (100, 500, 1000), True),
}


def _do(db, uid: int, key: str, amount) -> str:
    """اجرای عملیات و برگرداندن پیام کوتاه نتیجه (متن ساده برای toast)"""
    if key == "dep":
        a, _ = db.deposit(uid, amount)
        return f"✅ {fmt_num(a)} 🪙 به بانک واریز شد"
    if key == "wd":
        a, _ = db.withdraw(uid, amount)
        return f"✅ {fmt_num(a)} 🪙 به کیف پولت برگشت"
    if key == "inv":
        a, total = db.invest(uid, amount)
        return f"📈 {fmt_num(a)} 🪙 سرمایه‌گذاری شد. کل سرمایه: {fmt_num(total)}"
    if key == "div":
        a, _ = db.divest(uid, amount)
        return f"📉 {fmt_num(a)} 🪙 به حساب بانکی برگشت"
    if key == "loan":
        a, debt, _ = db.borrow(uid, amount)
        return f"💳 وام {fmt_num(a)} 🪙 گرفتی. بدهی: {fmt_num(debt)}"
    if key == "repay":
        a, left = db.repay(uid, amount)
        return f"✅ {fmt_num(a)} 🪙 پرداخت شد. بدهی باقی‌مانده: {fmt_num(left)}"
    raise GameError("عملیات نامعتبر")


async def _show_menu(c: Ctx, edit: bool = False) -> None:
    p = c.db.get_player(c.user.id)
    uid = c.user.id
    if not p["bank_open"]:
        text = (
            f"{head('🏦', 'بانک روسی')}\n"
            "😕 هنوز بانک نداری!\n\n"
            f"🏗 هزینه‌ی تاسیس: {coins(config.BANK_FOUNDING_COST)}\n"
            f"💵 کیف پولت: {coins(p['coins'])}\n\n"
            "<blockquote>بعد از تاسیس می‌تونی پول جا‌به‌جا کنی، سرمایه‌گذاری کنی و وام بگیری ✨</blockquote>"
        )
        markup = kb([[("🏦 تاسیس بانک", f"bank:open:{uid}")]])
    else:
        text = _summary(p) + _footer()
        markup = kb([
            [("💵 واریز", f"bank:pick:dep:{uid}"), ("🏛 برداشت", f"bank:pick:wd:{uid}")],
            [("📈 سرمایه‌گذاری", f"bank:pick:inv:{uid}"), ("📉 برداشت سرمایه", f"bank:pick:div:{uid}")],
            [("💳 وام", f"bank:pick:loan:{uid}"), ("✅ پرداخت وام", f"bank:pick:repay:{uid}")],
            [("💸 انتقال به دیگران", f"bank:xfer:{uid}"), ("🔄 بروزرسانی", f"bank:menu:{uid}")],
        ])
    if edit:
        await c.edit(text, markup)
    else:
        await c.reply(text, reply_markup=markup)


async def _show_picker(c: Ctx, key: str) -> None:
    emoji, title, label, avail_fn, presets, allow_all = _ACTIONS[key]
    p = c.db.get_player(c.user.id)
    avail = avail_fn(p)
    uid = c.user.id
    options = [(fmt_num(v), f"bank:do:{key}:{v}:{uid}") for v in presets if v <= avail]
    if allow_all and avail > 0:
        options.append(("✨ همه", f"bank:do:{key}:all:{uid}"))
    if not options:
        raise GameError(f"{label} برای این کار کافی نیست (الان: {fmt_num(avail)} 🪙).")
    rows = [options[i:i + 3] for i in range(0, len(options), 3)]
    rows.append([("🔙 بازگشت", f"bank:menu:{uid}")])
    await c.edit(f"{head(emoji, title)}\n{label}: {coins(avail)}\n\n👇 <b>مبلغ رو انتخاب کن</b>", kb(rows))


@text_command(r"بانک روسی")
async def bank_menu(c: Ctx) -> None:
    await _show_menu(c)


@callback("bank")
async def bank_buttons(c: Ctx) -> None:
    c.require_owner()
    action = c.args[0]
    if action == "open":
        c.db.open_bank(c.user.id, config.BANK_FOUNDING_COST)
        await c.answer("🎉 بانکت تاسیس شد!")
    elif action == "pick":
        await _show_picker(c, c.args[1])
        return
    elif action == "do":
        key, raw = c.args[1], c.args[2]
        toast = _do(c.db, c.user.id, key, None if raw == "all" else int(raw))
        await c.answer(toast)
    elif action == "xfer":
        await c.answer(
            "💸 برای انتقال، روی پیام طرف ریپلای کن و بنویس: انتقال 100\nیا بنویس: انتقال 100 @یوزرنیم",
            alert=True,
        )
        return
    await _show_menu(c, edit=True)


@text_command(rf"واریز {AMT}")
async def deposit(c: Ctx) -> None:
    amt, bal = c.db.deposit(c.user.id, parse_amount(c.match["amount"]))
    await c.reply(receipt("✅", "واریز شد", f"💵 مبلغ: {coins(amt)}", f"🏛 موجودی بانک: {coins(bal)}"))


@text_command(rf"برداشت {AMT}")
async def withdraw(c: Ctx) -> None:
    amt, wallet = c.db.withdraw(c.user.id, parse_amount(c.match["amount"]))
    await c.reply(receipt("✅", "برداشت شد", f"💵 مبلغ: {coins(amt)}", f"💰 کیف پول: {coins(wallet)}"))


@text_command(rf"انتقال {AMT}(?: @(?P<username>\w+))?")
async def transfer(c: Ctx) -> None:
    amount = parse_amount(c.match["amount"])
    target_id, target_name = None, None

    if c.match["username"]:
        row = c.db.get_player_by_username(c.match["username"])
        if row:
            target_id, target_name = row["user_id"], row["full_name"]
    else:
        r = c.message.reply_to_message
        if r and r.from_user and not r.from_user.is_bot and not r.forum_topic_created:
            u = r.from_user
            c.db.touch(u.id, u.username, u.full_name, c.chat.id)
            target_id, target_name = u.id, u.full_name

    if target_id is None:
        raise GameError("گیرنده مشخص نیست. روی پیامش ریپلای کن یا بنویس: انتقال 100 @یوزرنیم\n"
                        "(اگه یوزرنیم رو نمی‌شناسم، اون آدم باید یه بار توی ربات پیام داده باشه)")

    amt, bal = c.db.transfer(c.user.id, target_id, amount)
    await c.reply(receipt(
        "💸", "مبلغ منتقل شد",
        f"👤 گیرنده: <b>{esc(target_name)}</b>",
        f"💵 مبلغ: {coins(amt)}",
        f"🏛 موجودی بانک تو: {coins(bal)}",
    ))


@text_command(rf"سرمایه گذاری {AMT}")
async def invest(c: Ctx) -> None:
    amt, total = c.db.invest(c.user.id, parse_amount(c.match["amount"]))
    await c.reply(receipt(
        "📈", "سرمایه‌گذاری شد",
        f"💵 مبلغ: {coins(amt)}",
        f"🧮 کل سرمایه: {coins(total)}",
        f"🌙 سود امشب ساعت ۱۲ (تهران): <b>+{fmt_num(game.tonight_profit(total))}</b> 🪙",
    ))


@text_command(rf"برداشت سرمایه {AMT}")
async def divest(c: Ctx) -> None:
    amt, left = c.db.divest(c.user.id, parse_amount(c.match["amount"]))
    await c.reply(receipt("📉", "سرمایه به حساب بانکی برگشت", f"💵 مبلغ: {coins(amt)}", f"🧮 سرمایه‌ی باقی‌مانده: {coins(left)}"))


@text_command(rf"وام {AMT}")
async def loan(c: Ctx) -> None:
    amt, debt, bal = c.db.borrow(c.user.id, parse_amount(c.match["amount"]))
    await c.reply(receipt(
        "💳", "وام دریافت شد",
        f"💵 مبلغ وام: {coins(amt)}",
        f"📛 بدهی کل (با کارمزد): {coins(debt)}",
        f"⏳ بهره‌ی شبانه: <b>{config.LOAN_DAILY_PERCENT}٪</b>",
        f"🏛 موجودی بانک: {coins(bal)}",
    ))


@text_command(rf"پرداخت وام(?: {AMT})?")
async def repay(c: Ctx) -> None:
    raw = c.match["amount"]
    amt, left = c.db.repay(c.user.id, parse_amount(raw) if raw else None)
    await c.reply(receipt("✅", "بدهی پرداخت شد", f"💵 مبلغ: {coins(amt)}", f"💳 بدهی باقی‌مانده: {coins(left)}"))
