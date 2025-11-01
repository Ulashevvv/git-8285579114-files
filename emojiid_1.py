# meta developer: @reewi
# scope: inline
# requires: hikka

from telethon.tl.types import MessageEntityCustomEmoji
from telethon.tl.functions.messages import GetCustomEmojiDocumentsRequest
from .. import loader, utils

@loader.tds
class EmojiIDMod(loader.Module):
    """Ko‘rsatuvchi modul: Emoji ID (oddiy + premium)"""
    strings = {
        "name": "EmojiID",
        "no_reply": "❌ Javob sifatida emoji yuborilgan xabarni tanlang.",
        "no_emoji": "❌ Hech qanday emoji topilmadi.",
        "result_premium": (
            "🌟 <b>Premium Emoji</b>\n"
            "Emoji: <code>{emoji}</code>\n"
            "🆔 <code>{emoji_id}</code>\n"
            "📄 document_id: <code>{doc_id}</code>"
        ),
        "result_regular": (
            "🔹 <b>Oddiy Emoji</b>\n"
            "Emoji: <code>{emoji}</code>\n"
            "Unicode ID: <code>{unicode}</code>"
        ),
        "footer": "\n\n<i>Обновил код: @reewi</i>"
    }

    async def midcmd(self, message):
        """Emoji haqida ID va tafsilotlar beradi"""
        reply = await message.get_reply_message()
        if not reply or not reply.raw_text:
            return await utils.answer(message, self.strings("no_reply"))

        output = []
        copy_texts = []

        # --- Premium emoji tekshirish ---
        custom_emojis = [
            e for e in (reply.entities or [])
            if isinstance(e, MessageEntityCustomEmoji)
        ]

        if custom_emojis:
            emoji_ids = [e.document_id for e in custom_emojis]
            result = await message.client(GetCustomEmojiDocumentsRequest(emoji_ids))

            for e, doc in zip(custom_emojis, result):
                emoji_char = reply.raw_text[e.offset : e.offset + e.length]
                output.append(self.strings("result_premium").format(
                    emoji=emoji_char,
                    emoji_id=e.document_id,
                    doc_id=doc.id
                ))
                # faqat <emoji ...>...</emoji> formatida
                copy_texts.append(f"<emoji document_id={doc.id}>{emoji_char}</emoji>")

        # --- Oddiy emoji (Unicode) ---
        for ch in reply.raw_text:
            if ch.isspace():
                continue
            cp = ord(ch)
            if cp > 0x1F000 or (0x2100 <= cp <= 0x27BF):
                output.append(self.strings("result_regular").format(
                    emoji=ch,
                    unicode=f"U+{cp:04X}"
                ))
                # oddiy emoji uchun faqat emoji belgisi
                copy_texts.append(ch)

        if not output:
            return await utils.answer(message, self.strings("no_emoji"))

        # --- Natija chiqarish ---
        text = "\n\n".join(output) + self.strings("footer")
        copy_str = " ".join(copy_texts)  # bir qatorda

        await self.inline.form(
            message=message,
            text=text,
            reply_markup=[
                [{"text": " Скопировать", "copy": copy_str}],
            ],
        )