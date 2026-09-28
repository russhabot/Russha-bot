import random
import re
import time

import config
from router import Ctx, text_command
from ui import LINE, coins, esc
from utils import fmt_duration, normalize

_PATTERN = "|".join(re.escape(normalize(t)) for t in config.PRIVET_TRIGGERS)
_FACE = {1: "🙂", 2: "😄", 3: "😎", 4: "🤩", 5: "🎉"}


@text_command(_PATTERN, search=True)
async def privet(c: Ctx) -> None:
    reward = random.randint(config.REWARD_MIN, config.REWARD_MAX)
    ok, wallet, remaining = c.db.claim_privet(c.user.id, int(time.time()), config.COOLDOWN_SECONDS, reward)
    name = esc(c.user.first_name)
    if ok:
        await c.reply(
            f"👋 <b>پریویت {name}!</b>\n{LINE}\n"
            f"{_FACE.get(reward, '🎁')} پاداش: <b>+{reward}</b> راشا کوین 🪙\n"
            f"💰 کیف پول: {coins(wallet)}\n"
            f"⏱ پریویت بعدی: {fmt_duration(config.COOLDOWN_SECONDS)} دیگه"
        )
    else:
        await c.reply(
            f"⏳ <b>هنوز زوده {name}!</b>\n{LINE}\n"
            f"⌛ {fmt_duration(remaining)} دیگه صبر کن\n"
            f"💰 کیف پول: {coins(wallet)}"
        )
