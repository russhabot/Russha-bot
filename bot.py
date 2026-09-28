import datetime
import logging
from zoneinfo import ZoneInfo

from telegram import BotCommandScopeAllPrivateChats, MenuButtonDefault
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters

import config
import features  # noqa: F401  (ثبت دستورهای متنی)
import router
from db import Database

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
log = logging.getLogger("bot")


async def nightly_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """سود سرمایه‌گذاری و بهره‌ی وام؛ ساعت ۰۰:۰۰ به وقت تهران"""
    today = datetime.datetime.now(ZoneInfo(config.TIMEZONE)).date()
    days = context.application.bot_data["db"].run_nightly(today)
    if days:
        log.info("سود/بهره‌ی شبانه برای %s شب اعمال شد", days)


async def post_init(app: Application) -> None:
    """ربات فقط در گروه کار می‌کند؛ هر منوی دستور یا دکمه‌ی مخصوص پیوی که قبلاً ثبت شده پاک می‌شود"""
    await app.bot.delete_my_commands()
    await app.bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())


def main() -> None:
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    if app.job_queue is None:
        raise SystemExit("job-queue نصب نیست: pip install -r requirements.txt")
    app.bot_data["db"] = Database(config.DB_PATH)

    app.add_handler(CallbackQueryHandler(router.on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, router.on_text))
    app.add_error_handler(router.on_error)

    tz = ZoneInfo(config.TIMEZONE)
    app.job_queue.run_daily(nightly_job, time=datetime.time(0, 0, 5, tzinfo=tz), name="nightly")
    app.job_queue.run_once(nightly_job, when=3, name="nightly_catchup")  # جبران شب‌هایی که ربات خاموش بود

    app.run_polling()


if __name__ == "__main__":
    main()
