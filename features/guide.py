import config
from router import Ctx, text_command
from ui import head


def help_text() -> str:
    return (
        f"{head('🤖', 'راهنمای ربات راشا کوین')}\n"
        "همه‌چیز فقط با نوشتن متن ساده توی گروه انجام می‌شه ✨\n\n"
        "<blockquote>"
        f"👋 <b>پریویت</b> یا <b>привет</b>\n"
        f"🎁 {config.REWARD_MIN} تا {config.REWARD_MAX} راشا کوین 🪙 هر {config.COOLDOWN_SECONDS // 60} دقیقه\n"
        "🌍 توی همه‌ی گروه‌ها یکسانه"
        "</blockquote>\n"
        "<blockquote>"
        "📊 <b>وضعیت</b>\n"
        "💰 کیف پول، بانک، ودکا ساز و آمار تو"
        "</blockquote>\n"
        "<blockquote>"
        "🏦 <b>بانک روسی</b>\n"
        "🔹 تاسیس بانک و واریز و برداشت\n"
        f"📈 سرمایه‌گذاری با سود {config.INVEST_DAILY_PERCENT}٪ هر شب ساعت ۱۲ (تهران)\n"
        "💳 وام و پرداخت وام\n"
        "💸 انتقال به دیگران: روی پیامشون ریپلای کن و بنویس <b>انتقال 100</b>\n"
        "     یا بنویس <b>انتقال 100 @یوزرنیم</b>"
        "</blockquote>\n"
        "<blockquote>"
        "🍶 <b>ودکا ساز</b>\n"
        "⚙️ دستگاه شخصی که حتی وقتی آفلاینی راشا کوین تولید می‌کنه\n"
        "📦 ظرفیت داره و باید برداشت کنی تا دوباره پر بشه\n"
        "⬆️ قابل ارتقاست"
        "</blockquote>\n"
        "<blockquote>"
        "🏆 <b>برترین روس</b>\n"
        "🏠 جدول همین گروه یا 🌍 جهانی"
        "</blockquote>\n"
        "❓ <b>راهنما</b> — همین پیام"
    )


@text_command(r"(?:راهنما|راهنمایی|help)")
async def guide(c: Ctx) -> None:
    await c.reply(help_text())
