import asyncio

from pyrogram import filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait

from AnonXMusic import app
from AnonXMusic.misc import SUDOERS
from AnonXMusic.utils.database import (
    get_active_chats,
    get_authuser_names,
    get_client,
    get_served_chats,
    get_served_users,
    save_broadcast_stats,
)
from AnonXMusic.utils.decorators.language import language
from AnonXMusic.utils.formatters import alpha_to_int
from config import adminlist

__MODULE__ = "Broadcast"
__HELP__ = """
/broadcast [mesaj] veya mesajı yanıtla
Yayını desteklenen tüm gruplara yollar.

Ek seçenekler:
-pin - Mesajı sabitler
-pinloud - Gürültülü sabitler
-assistant - Asistan hesaplarıyla yollar
-user - Kullanıcılara yollar
-nobot - Ana bottan göndermez
"""

IS_BROADCASTING = False


@app.on_message(filters.command("broadcast") & SUDOERS)
@language
async def braodcast_message(client, message, _):
    global IS_BROADCASTING
    if IS_BROADCASTING:
        return await message.reply_text("Zaten bir yayın işlemi devam ediyor.")

    if message.reply_to_message:
        msg_id = message.reply_to_message.id
        chat_id = message.chat.id
        content = None
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_2"])
        content = message.text.split(None, 1)[1]
        if not content.replace("-pin", "").replace("-pinloud", "").replace("-nobot", "").replace("-assistant", "").replace("-user", "").strip():
            return await message.reply_text(_["broad_8"])

    IS_BROADCASTING = True
    ok = await message.reply_text(_["broad_1"])

    flags = message.text if not message.reply_to_message else ""
    sent, pinned, user_sent, assistant_sent = 0, 0, 0, 0

    if "-nobot" not in flags:
        chats = [int(c["chat_id"]) for c in await get_served_chats()]
        for chat in chats:
            try:
                m = (
                    await app.forward_messages(chat, chat_id, msg_id)
                    if message.reply_to_message
                    else await app.send_message(chat, text=content)
                )
                if "-pin" in flags:
                    try:
                        await m.pin(disable_notification=True)
                        pinned += 1
                    except:
                        pass
                elif "-pinloud" in flags:
                    try:
                        await m.pin(disable_notification=False)
                        pinned += 1
                    except:
                        pass
                sent += 1
                await asyncio.sleep(0.3)
            except FloodWait as fw:
                await asyncio.sleep(fw.value)
            except:
                continue

    if "-user" in flags:
        users = [int(u["user_id"]) for u in await get_served_users()]
        for user_id in users:
            try:
                if message.reply_to_message:
                    await app.forward_messages(user_id, chat_id, msg_id)
                else:
                    await app.send_message(user_id, text=content)
                user_sent += 1
                await asyncio.sleep(0.3)
            except FloodWait as fw:
                await asyncio.sleep(fw.value)
            except:
                continue

    if "-assistant" in flags:
        from AnonXMusic.core.userbot import assistants
        for num in assistants:
            client = await get_client(num)
            async for dialog in client.get_dialogs():
                try:
                    if message.reply_to_message:
                        await client.forward_messages(dialog.chat.id, chat_id, msg_id)
                    else:
                        await client.send_message(dialog.chat.id, text=content)
                    assistant_sent += 1
                    await asyncio.sleep(3)
                except FloodWait as fw:
                    await asyncio.sleep(fw.value)
                except:
                    continue

    await save_broadcast_stats(message.from_user.id, content if content else "Medya", sent, user_sent, assistant_sent)
    try:
        await ok.edit_text(_["broad_3"].format(sent, pinned))
    except:
        pass

    IS_BROADCASTING = False


# Adminleri otomatik güncelleyen görev
async def auto_clean():
    while True:
        await asyncio.sleep(30)
        try:
            served_chats = await get_active_chats()
            for chat_id in served_chats:
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                async for user in app.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
                    if user.privileges.can_manage_video_chats:
                        adminlist[chat_id].append(user.user.id)
                authusers = await get_authuser_names(chat_id)
                for auth in authusers:
                    user_id = await alpha_to_int(auth)
                    adminlist[chat_id].append(user_id)
        except:
            continue

asyncio.create_task(auto_clean())
