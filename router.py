"""مسیریاب دستورهای متنی و دکمه‌ها.

افزودن دستور متنی جدید:
    @text_command(r"الگوی regex روی متن نرمال‌شده")
    async def my_cmd(c: Ctx): await c.reply("سلام")

افزودن دکمه‌ی شیشه‌ای جدید (callback_data به شکل  prefix:arg1:arg2 ):
    @callback("prefix")
    async def my_cb(c: Ctx): ...   # c.args == ["arg1", "arg2"]
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from telegram import CallbackQuery, Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update, User
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from db import Database
from errors import GameError
from ui import esc
from utils import normalize

log = logging.getLogger(__name__)

_FULL: list[tuple[re.Pattern, Callable]] = []    # کل پیام باید با الگو یکی باشد
_SEARCH: list[tuple[re.Pattern, Callable]] = []  # الگو می‌تواند هرجای پیام باشد (بعد از دستورهای کامل بررسی می‌شود)
_CALLBACKS: dict[str, Callable] = {}


def text_command(pattern: str, search: bool = False):
    def deco(fn):
        (_SEARCH if search else _FULL).append((re.compile(pattern), fn))
        return fn
    return deco


def callback(prefix: str):
    def deco(fn):
        _CALLBACKS[prefix] = fn
        return fn
    return deco


def kb(rows: list[list[tuple[str, str]]]) -> Optional[InlineKeyboardMarkup]:
    """rows = [[(متن دکمه, callback_data), ...], ...]"""
    if not rows:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in row] for row in rows])


@dataclass
class Ctx:
    update: Update
    context: ContextTypes.DEFAULT_TYPE
    db: Database
    user: User
    chat: Chat
    message: Optional[Message]
    match: Optional[re.Match] = None
    query: Optional[CallbackQuery] = None
    args: list[str] = field(default_factory=list)
    answered: bool = field(default=False, init=False)

    async def reply(self, text: str, **kw):
        kw.setdefault("parse_mode", "HTML")
        return await self.message.reply_text(text, **kw)

    async def edit(self, text: str, markup=None):
        try:
            await self.query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise

    async def answer(self, text: Optional[str] = None, alert: bool = False):
        self.answered = True
        await self.query.answer(text, show_alert=alert)

    def require_owner(self) -> None:
        """آخرین آرگومان دکمه باید آیدی کسی باشد که روی آن می‌زند"""
        if not self.args or self.args[-1] != str(self.user.id):
            raise GameError("این منو مال تو نیست 🙂 خودت بنویس.")


GROUP_TYPES = ("group", "supergroup")


def _in_group(chat: Optional[Chat]) -> bool:
    """ربات فقط داخل گروه‌ها کار می‌کند؛ پیوی کاملاً نادیده گرفته می‌شود."""
    return chat is not None and chat.type in GROUP_TYPES


def _touch(db: Database, user: User, chat: Chat) -> None:
    db.touch(user.id, user.username, user.full_name, chat.id)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg, user = update.effective_message, update.effective_user
    if not msg or not msg.text or not user or user.is_bot or not _in_group(update.effective_chat):
        return
    text = normalize(msg.text)

    fn, match = None, None
    for rx, f in _FULL:
        if (m := rx.fullmatch(text)):
            fn, match = f, m
            break
    if fn is None:
        for rx, f in _SEARCH:
            if (m := rx.search(text)):
                fn, match = f, m
                break
    if fn is None:
        return

    db: Database = context.application.bot_data["db"]
    chat = update.effective_chat
    _touch(db, user, chat)
    c = Ctx(update, context, db, user, chat, msg, match=match)
    try:
        await fn(c)
    except GameError as e:
        await c.reply(f"⚠️ {esc(str(e))}")


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q is None:
        return
    if not _in_group(update.effective_chat):
        await q.answer()
        return
    parts = (q.data or "").split(":")
    fn = _CALLBACKS.get(parts[0])
    if fn is None:
        await q.answer()
        return

    db: Database = context.application.bot_data["db"]
    chat = update.effective_chat
    _touch(db, q.from_user, chat)
    c = Ctx(update, context, db, q.from_user, chat, q.message, query=q, args=parts[1:])
    try:
        await fn(c)
    except GameError as e:
        await c.answer(str(e), alert=True)
    if not c.answered:
        await q.answer()


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("خطا در پردازش آپدیت", exc_info=context.error)
