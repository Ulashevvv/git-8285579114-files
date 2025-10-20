# meta developer: @reewi
# meta name: SocialSave
# meta version: 13.0
# meta description: Instagram va YouTube musiqa yuklab olish

from telethon.tl.types import Message
from .. import loader, utils
import aiohttp
import os
import re
import yt_dlp


@loader.tds
class SocialSaveMod(loader.Module):
    """Instagram va YouTube musiqa yuklab olish"""
    strings = {
        "name": "SocialSave",
        "loading": "⏳ Yuklanmoqda...",
        "error": "❌ Xatolik: {}",
        "saved": "✅ Saqlandi.\n📌 @reewi_moduls",
        "saved_song": "✅ Yuklandi: {} 🎵",
    }

    # 📌 INSTAGRAM yuklash (.save)
    async def savecmd(self, message: Message):
        """Instagram video/photo yuklab olish: .save <url> yoki reply"""
        url = await self._get_url(message)
        if not url:
            return await utils.answer(message, "❌ Havola topilmadi")

        loading = await utils.answer(message, self.strings("loading"))
        try:
            api_url = f"https://dev.xspin.uz?url={url}"
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    data = await resp.json()

            photo = data.get("photo")
            video = data.get("video")

            # 🔹 VIDEO yuklab olish
            if video:
                filename = "insta_video.mp4"
                async with aiohttp.ClientSession() as session:
                    async with session.get(video) as resp:
                        with open(filename, "wb") as f:
                            f.write(await resp.read())

                await self._client.send_file(
                    message.chat_id,
                    filename,
                    caption=self.strings("saved"),
                    reply_to=message.reply_to_msg_id
                )
                try:
                    os.remove(filename)
                except FileNotFoundError:
                    pass

            # 🔹 PHOTO yuklab olish
            elif photo:
                filename = "insta_photo.jpg"
                async with aiohttp.ClientSession() as session:
                    async with session.get(photo) as resp:
                        with open(filename, "wb") as f:
                            f.write(await resp.read())

                await self._client.send_file(
                    message.chat_id,
                    filename,
                    caption=self.strings("saved"),
                    reply_to=message.reply_to_msg_id
                )
                try:
                    os.remove(filename)
                except FileNotFoundError:
                    pass

            else:
                await utils.answer(message, "❌ Media topilmadi")

        except Exception as e:
            await utils.answer(message, self.strings("error").format(str(e)))
        finally:
            await loading.delete()

    async def _get_url(self, message: Message):
        args = utils.get_args_raw(message)
        url = None

        if message.is_reply:
            reply = await message.get_reply_message()
            if reply and reply.raw_text:
                match = re.search(r"(https?://[^\s]+)", reply.raw_text)
                if match:
                    url = match.group(1)

        if not url and args and args.startswith("http"):
            url = args.strip()

        return url

    # 📌 MUSIQA (YouTube qidiruvdan MP3)
    async def songcmd(self, message: Message):
        """<nomi> - YouTube qidiruv orqali musiqa yuklab olish"""
        query = utils.get_args_raw(message)
        if not query:
            return await utils.answer(message, "❌ Musiqa nomini yozing. Masalan: `.song Billie Jean`")

        loading = await utils.answer(message, self.strings("loading"))

        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "noplaylist": True,
                "outtmpl": "music.%(ext)s",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=True)["entries"][0]
                filename = ydl.prepare_filename(info)
                filename = os.path.splitext(filename)[0] + ".mp3"
                title = info.get("title", "Musiqa")

            if os.path.exists(filename):
                await self._client.send_file(
                    message.chat_id,
                    filename,
                    caption=self.strings("saved_song").format(title),
                    reply_to=message.reply_to_msg_id
                )
                try:
                    os.remove(filename)
                except FileNotFoundError:
                    pass
            else:
                await utils.answer(message, "❌ Musiqa yuklab olinmadi")

        except Exception as e:
            await utils.answer(message, self.strings("error").format(str(e)))
        finally:
            await loading.delete()