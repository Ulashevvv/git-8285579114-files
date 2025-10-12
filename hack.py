# -*- coding: utf-8 -*-
# DM -> Channel (errors only to channel)
# Author: (for @reewi)
# Description: DM xabarlarini kanalga yuboradi. .send bilan birdaniga o'chirilgan xabarlarni delet.txt fayl sifatida yuboradi.
# Note: .cfg orqali CHANNEL_ID, DELETED_CHANNEL_ID, .sed/.seed ishlaydi.

import os
import traceback
import asyncio
import json
from datetime import datetime
from .. import loader, utils
from telethon import events
from telethon.tl.types import Message, User
from telethon.tl.functions.account import UpdateStatusRequest

@loader.tds
class DMToChannelErrToChannelMod(loader.Module):
    """DM -> Channel; .send bilan birdaniga o'chirilgan xabarlarni delet.txt fayl sifatida yuboradi"""
    strings = {"name": "DMToChannelErrToChannel"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "CHANNEL_ID", None, "Asosiy kanal ID (-100 bilan boshlanadi, masalan: -1001234567890)",
            "DELETED_CHANNEL_ID", None, "O'chirilgan xabarlar kanali ID (-100 bilan boshlanadi)"
        )
        self._online_status_set = False
        self._deleted_messages = []
        self._maps = {}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

        try:
            if self.db.get("DMToChannelErrToChannel", "enabled") is None:
                self.db.set("DMToChannelErrToChannel", "enabled", False)

            try:
                saved_maps = self.db.get("DMToChannelErrToChannel", "maps")
                if saved_maps and isinstance(saved_maps, dict):
                    self._maps = saved_maps
                else:
                    self._maps = {}
            except Exception:
                self._maps = {}

            try:
                saved_deleted = self.db.get("DMToChannelErrToChannel", "deleted_messages")
                if saved_deleted and isinstance(saved_deleted, list):
                    self._deleted_messages = saved_deleted
                else:
                    self._deleted_messages = []
            except Exception:
                self._deleted_messages = []

        except Exception:
            self.db.set("DMToChannelErrToChannel", "enabled", False)
            self._maps = {}
            self._deleted_messages = []

        if not self._online_status_set:
            try:
                await self.client(UpdateStatusRequest(offline=True))
                self._online_status_set = True
            except Exception:
                pass
        
        try:
            self.client.add_event_handler(
                self._on_delete_highlevel, 
                events.MessageDeleted
            )
        except Exception:
            pass

    def _safe_db_set(self, key, value):
        """Database ga xavfsiz yozish"""
        try:
            json.dumps(value)
            self.db.set("DMToChannelErrToChannel", key, value)
            return True
        except Exception:
            try:
                if key == "maps":
                    simple_maps = {}
                    for k, v in value.items():
                        if isinstance(v, list):
                            simple_maps[str(k)] = []
                            for item in v:
                                if isinstance(item, dict):
                                    simple_item = {}
                                    for ik, iv in item.items():
                                        simple_item[str(ik)] = str(iv) if not isinstance(iv, (int, float, bool, type(None))) else iv
                                    simple_maps[str(k)].append(simple_item)
                    self.db.set("DMToChannelErrToChannel", key, simple_maps)
                elif key == "deleted_messages":
                    simple_list = []
                    for item in value:
                        if isinstance(item, dict):
                            simple_item = {}
                            for ik, iv in item.items():
                                simple_item[str(ik)] = str(iv) if not isinstance(iv, (int, float, bool, type(None))) else iv
                            simple_list.append(simple_item)
                    self.db.set("DMToChannelErrToChannel", key, simple_list)
                else:
                    self.db.set("DMToChannelErrToChannel", key, str(value))
                return True
            except Exception:
                return False

    async def _get_user_info(self, user_id):
        """Foydalanuvchi ma'lumotlarini olish"""
        try:
            user = await self.client.get_entity(user_id)
            username = f"@{user.username}" if user.username else "Yo'q"
            first_name = user.first_name or "Yo'q"
            last_name = user.last_name or ""
            
            full_name = first_name
            if last_name:
                full_name += f" {last_name}"
                
            return {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name,
                "user_id": user_id
            }
        except Exception:
            return {
                "username": "Yo'q",
                "first_name": "Noma'lum",
                "last_name": "",
                "full_name": "Noma'lum",
                "user_id": user_id
            }

    async def sedcmd(self, message: Message):
        """.sed — modulni yoqish"""
        try:
            self.db.set("DMToChannelErrToChannel", "enabled", True)
            await message.edit("✅ DM->Channel modul **yoqildi**.\n📝 .send bilan birdaniga o'chirilgan xabarlarni delet.txt fayl sifatida olasiz.")
        except Exception as e:
            await message.edit(f"❌ Xato: {str(e)}")

    async def seedcmd(self, message: Message):
        """.seed — modulni o'chirish"""
        try:
            self.db.set("DMToChannelErrToChannel", "enabled", False)
            await message.edit("🛑 DM->Channel modul **o'chirildi**.")
        except Exception as e:
            await message.edit(f"❌ Xato: {str(e)}")

    async def statuscmd(self, message: Message):
        """.status — modul holatini ko'rsatish"""
        try:
            enabled = self.db.get("DMToChannelErrToChannel", "enabled", False)
        except Exception:
            enabled = False
            
        channel_id = self.config["CHANNEL_ID"]
        deleted_channel_id = self.config["DELETED_CHANNEL_ID"]
        deleted_count = len(self._deleted_messages)
        
        status_text = f"📊 **DMToChannel Modul Holati:**\n"
        status_text += f"• **Holat:** {'✅ Yoqilgan' if enabled else '❌ Oʻchirilgan'}\n"
        status_text += f"• **Asosiy kanal:** `{channel_id or '❌ Oʻrnatilmagan'}`\n"
        status_text += f"• **Hisobot kanali:** `{deleted_channel_id or '❌ Oʻrnatilmagan'}`\n"
        status_text += f"• **O'chirilgan xabarlar:** `{deleted_count} ta`\n"
        status_text += f"• **Online status:** {'❌ Oʻchirilgan' if self._online_status_set else '⚠️ Nomaʼlum'}"
        
        await message.edit(status_text)

    async def clearcmd(self, message: Message):
        """.clear — o'chirilgan xabarlar ro'yxatini tozalash"""
        self._deleted_messages = []
        self._safe_db_set("deleted_messages", [])
        await message.edit("✅ O'chirilgan xabarlar ro'yxati tozalandi.")

    async def sendcmd(self, message: Message):
        """.send — birdaniga o'chirilgan xabarlarni delet.txt fayl sifatida YOZILGAN JOYGA yuborish"""
        try:
            # O'chirilgan xabarlar mavjudligini tekshirish
            if not self._deleted_messages:
                await message.edit("❌ Hozircha o'chirilgan xabarlar mavjud emas.")
                return

            # .send YOZILGAN JOYGA delet.txt yuborish
            success = await self._send_deleted_report_to_current_chat(message)
            if success:
                await message.edit(f"✅ O'chirilgan xabarlar delet.txt fayli sifatida **ushbu chatga** yuborildi! ({len(self._deleted_messages)} ta)")
            else:
                await message.edit("❌ Delet.txt faylini yuborishda xatolik yuz berdi.")
            
        except Exception as e:
            await message.edit(f"❌ Xatolik: {str(e)}")

    async def _send_deleted_report_to_current_chat(self, message):
        """O'chirilgan xabarlarni .send YOZILGAN JOYGA delet.txt fayl sifatida yuborish"""
        try:
            if not self._deleted_messages:
                return False

            # delet.txt fayl yaratish
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"delet_{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"O'CHIRILGAN XABARLAR HISOBOTI\n")
                f.write(f"Yaratilgan vaqti: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Jami xabarlar: {len(self._deleted_messages)}\n")
                f.write("=" * 60 + "\n\n")
                
                for i, msg_data in enumerate(self._deleted_messages, 1):
                    f.write(f"{i}. XABAR MA'LUMOTLARI:\n")
                    f.write(f"   📝 Xabar ID: {msg_data.get('message_id', 'N/A')}\n")
                    f.write(f"   🆔 Foydalanuvchi ID: {msg_data.get('user_id', 'N/A')}\n")
                    f.write(f"   👤 Username: {msg_data.get('username', 'N/A')}\n")
                    f.write(f"   📛 Ism: {msg_data.get('first_name', 'N/A')}\n")
                    f.write(f"   👥 To'liq ism: {msg_data.get('full_name', 'N/A')}\n")
                    f.write(f"   ⏰ Vaqt: {msg_data.get('timestamp', 'N/A')}\n")
                    f.write(f"   💬 Matn: {msg_data.get('text', 'N/A')}\n")
                    f.write(f"   📍 Kanaldan: {msg_data.get('channel_id', 'N/A')}\n")
                    f.write(f"   💬 Chat ID: {msg_data.get('chat_id', 'N/A')}\n")
                    f.write("-" * 50 + "\n")

            # delet.txt faylni .send YOZILGAN JOYGA yuborish
            with open(filename, "rb") as f:
                await self.client.send_file(
                    message.chat_id,  # .send yozilgan chat ID
                    f,
                    caption=f"🗑️ O'chirilgan xabarlar hisoboti ({len(self._deleted_messages)} ta)\n⏰ Vaqt: {datetime.now().strftime('%H:%M:%S')}"
                )

            # Faylni o'chirish
            try:
                os.remove(filename)
            except Exception:
                pass
            
            # O'chirilgan xabarlar ro'yxatini tozalash
            self._deleted_messages = []
            self._safe_db_set("deleted_messages", [])
            
            return True
            
        except Exception as e:
            print(f"Delet.txt yuborishda xato: {e}")
            return False

    async def sendtocmd(self, message: Message):
        """.sendto — o'chirilgan xabarlarni asosiy kanalga delet.txt fayl sifatida yuborish"""
        try:
            deleted_channel_id = self.config["DELETED_CHANNEL_ID"]
            if not deleted_channel_id:
                await message.edit("❌ Hisobot kanali ID o'rnatilmagan. .cfg faylida DELETED_CHANNEL_ID ni o'rnating.")
                return

            if not self._deleted_messages:
                await message.edit("❌ Hozircha o'chirilgan xabarlar mavjud emas.")
                return

            # Asosiy kanalga delet.txt yuborish
            success = await self._send_deleted_report_to_channel(deleted_channel_id)
            if success:
                await message.edit(f"✅ O'chirilgan xabarlar delet.txt fayli sifatida **kanalga** yuborildi! ({len(self._deleted_messages)} ta)")
            else:
                await message.edit("❌ Delet.txt faylini kanalga yuborishda xatolik yuz berdi.")
            
        except Exception as e:
            await message.edit(f"❌ Xatolik: {str(e)}")

    async def _send_deleted_report_to_channel(self, deleted_channel_id):
        """O'chirilgan xabarlarni asosiy kanalga delet.txt fayl sifatida yuborish"""
        try:
            if not self._deleted_messages:
                return False

            # delet.txt fayl yaratish
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"delet_{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"O'CHIRILGAN XABARLAR HISOBOTI\n")
                f.write(f"Yaratilgan vaqti: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Jami xabarlar: {len(self._deleted_messages)}\n")
                f.write("=" * 60 + "\n\n")
                
                for i, msg_data in enumerate(self._deleted_messages, 1):
                    f.write(f"{i}. XABAR MA'LUMOTLARI:\n")
                    f.write(f"   📝 Xabar ID: {msg_data.get('message_id', 'N/A')}\n")
                    f.write(f"   🆔 Foydalanuvchi ID: {msg_data.get('user_id', 'N/A')}\n")
                    f.write(f"   👤 Username: {msg_data.get('username', 'N/A')}\n")
                    f.write(f"   📛 Ism: {msg_data.get('first_name', 'N/A')}\n")
                    f.write(f"   👥 To'liq ism: {msg_data.get('full_name', 'N/A')}\n")
                    f.write(f"   ⏰ Vaqt: {msg_data.get('timestamp', 'N/A')}\n")
                    f.write(f"   💬 Matn: {msg_data.get('text', 'N/A')}\n")
                    f.write(f"   📍 Kanaldan: {msg_data.get('channel_id', 'N/A')}\n")
                    f.write(f"   💬 Chat ID: {msg_data.get('chat_id', 'N/A')}\n")
                    f.write("-" * 50 + "\n")

            # delet.txt faylni asosiy kanalga yuborish
            with open(filename, "rb") as f:
                await self.client.send_file(
                    int(deleted_channel_id),
                    f,
                    caption=f"🗑️ O'chirilgan xabarlar hisoboti ({len(self._deleted_messages)} ta)\n⏰ Vaqt: {datetime.now().strftime('%H:%M:%S')}"
                )

            # Faylni o'chirish
            try:
                os.remove(filename)
            except Exception:
                pass
            
            # O'chirilgan xabarlar ro'yxatini tozalash
            self._deleted_messages = []
            self._safe_db_set("deleted_messages", [])
            
            return True
            
        except Exception as e:
            print(f"Delet.txt kanalga yuborishda xato: {e}")
            return False

    async def watcher(self, message: Message):
        # Faqat private incoming xabarlar
        try:
            if not message.is_private or message.out:
                return

            try:
                enabled = self.db.get("DMToChannelErrToChannel", "enabled", False)
            except Exception:
                enabled = False
                
            if not enabled:
                return

            channel_id = self.config["CHANNEL_ID"]
            if not channel_id:
                return

            # Foydalanuvchi ma'lumotlarini olish
            user_info = await self._get_user_info(message.sender_id)
            
            user_info_block = (
                f"👤 **Foydalanuvchi ma'lumotlari:**\n"
                f"   📛 Ism: {user_info['first_name']}\n"
                f"   👥 To'liq ism: {user_info['full_name']}\n"
                f"   🆔 Username: {user_info['username']}\n"
                f"   💬 User ID: `{user_info['user_id']}`\n"
                f"   💬 Chat ID: `{message.chat_id}`"
            )

            sent = None

            # Media bilan ishlash
            if message.media:
                try:
                    file_path = await message.download_media()
                    caption = f"{message.text or ''}\n\n{user_info_block}" if message.text else user_info_block
                    sent = await self.client.send_file(
                        int(channel_id), 
                        file_path, 
                        caption=caption
                    )
                    # Local faylni tozalash
                    try:
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass

                except Exception as ex_download:
                    # Yuklash yoki yuborishda xato
                    err_txt = "".join(traceback.format_exception_only(type(ex_download), ex_download)).strip()
                    await self._send_error_to_channel(
                        channel_id, 
                        message, 
                        user_info_block, 
                        err_txt, 
                        context="download_or_send_media"
                    )
                    return

            else:
                # Matnli xabar
                try:
                    text = f"{message.text or ''}\n\n{user_info_block}"
                    sent = await self.client.send_message(int(channel_id), text)
                except Exception as ex_send_text:
                    err_txt = "".join(traceback.format_exception_only(type(ex_send_text), ex_send_text)).strip()
                    await self._send_error_to_channel(
                        channel_id, 
                        message, 
                        user_info_block, 
                        err_txt, 
                        context="send_text"
                    )
                    return

            # Mapping saqlash (O'CHIRILGAN XABARLAR KANALDA SAQLANADI)
            if sent:
                await self._save_message_mapping(message, sent, channel_id, user_info)

        except Exception as e:
            # Watcher ichidagi kutilmagan xatolik
            try:
                channel_id = self.config["CHANNEL_ID"]
                if channel_id:
                    err_txt = "".join(traceback.format_exception_only(type(e), e)).strip()
                    await self._send_error_to_channel(
                        channel_id, 
                        message if 'message' in locals() else None, 
                        "👤 Noma'lum foydalanuvchi", 
                        err_txt, 
                        context="watcher_unhandled"
                    )
            except Exception:
                pass

    async def _save_message_mapping(self, original_msg, sent_msg, channel_id, user_info):
        """Xabar mappinglarini saqlash (O'CHIRILGAN XABARLAR KANALDA SAQLANADI)"""
        try:
            # Asosiy kalit
            key_full = f"{original_msg.chat_id}:{original_msg.id}"
            key_msg = f"{original_msg.id}"
            
            # To'liq mapping data
            mapping_data = {
                "channel_id": str(channel_id),
                "channel_msg_id": str(sent_msg.id),
                "orig_chat": str(original_msg.chat_id),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": str(user_info['user_id']),
                "username": user_info['username'],
                "first_name": user_info['first_name'],
                "full_name": user_info['full_name'],
                "text": original_msg.text or "Media xabar",
                "chat_id": str(original_msg.chat_id)
            }
            
            # Mappinglarni yangilash
            if key_full not in self._maps:
                self._maps[key_full] = []
            self._maps[key_full].append(mapping_data)
            
            if key_msg not in self._maps:
                self._maps[key_msg] = []
            self._maps[key_msg].append(mapping_data)
            
            # Database ga saqlash
            self._safe_db_set("maps", self._maps)
            
        except Exception as e:
            # Mapping saqlashda xatolik
            try:
                channel_id = self.config["CHANNEL_ID"]
                if channel_id:
                    err_txt = "".join(traceback.format_exception_only(type(e), e)).strip()
                    await self._send_error_to_channel(
                        channel_id, 
                        original_msg, 
                        "Mapping error", 
                        err_txt, 
                        context="save_mapping"
                    )
            except Exception:
                pass

    async def _send_error_to_channel(self, channel_id, orig_message, user_info_block, error_text, context="error"):
        """Xatolik haqida ma'lumotni faqat kanalga yuboradi."""
        try:
            chan_id = int(channel_id)
        except Exception:
            return

        details = [
            f"⚠️ **XATOLIK ({context})**",
            f"**Error:** `{error_text}`"
        ]

        if orig_message:
            try:
                preview = orig_message.text or ""
            except Exception:
                preview = ""

            meta = f"**Orig chat_id:msg_id:** `{getattr(orig_message, 'chat_id', 'N/A')}:{getattr(orig_message, 'id', 'N/A')}`"
            if preview:
                preview_clean = preview.replace('`', "'")[:400]
                meta += f"\n**Text preview:** `{preview_clean}`"
            details.append(meta)

        details.append(f"**User:**\n{user_info_block}")
        msg = "\n\n".join(details)

        try:
            await self.client.send_message(chan_id, msg)
        except Exception:
            pass

    async def _on_delete_highlevel(self, event):
        """MessageDeleted event handler"""
        try:
            deleted_ids = getattr(event, "deleted_ids", [])
            if not deleted_ids:
                return

            if not self._maps:
                return

            for msg_id in deleted_ids:
                await self._process_deleted_message(msg_id)

        except Exception as e:
            try:
                channel_id = self.config["CHANNEL_ID"]
                if channel_id:
                    err_txt = "".join(traceback.format_exception_only(type(e), e)).strip()
                    await self._send_error_to_channel(
                        channel_id, 
                        None, 
                        "Delete handler error", 
                        err_txt, 
                        context="delete_handler"
                    )
            except Exception:
                pass

    async def _process_deleted_message(self, msg_id):
        """O'chirilgan xabarni qayta ishlash"""
        msg_id_str = str(msg_id)
        
        # Mappinglarni topish
        entries = self._maps.get(msg_id_str, [])
        suffix = f":{msg_id}"
        matching_keys = [k for k in self._maps.keys() if k.endswith(suffix)]
        
        # Barcha mos keladigan mappinglarni yig'ish
        to_process = entries.copy()
        for key in matching_keys:
            to_process.extend(self._maps.get(key, []))

        # Takrorlanishlarni olib tashlash
        seen = set()
        for item in to_process:
            identifier = f"{item.get('channel_id')}:{item.get('channel_msg_id')}"
            if identifier not in seen:
                seen.add(identifier)
                await self._add_to_deleted_list(item)

    async def _add_to_deleted_list(self, mapping):
        """O'chirilgan xabarni ro'yxatga qo'shish"""
        try:
            deleted_data = {
                "message_id": mapping.get("channel_msg_id", "N/A"),
                "channel_id": mapping.get("channel_id", "N/A"),
                "user_id": mapping.get("user_id", "N/A"),
                "username": mapping.get("username", "N/A"),
                "first_name": mapping.get("first_name", "N/A"),
                "full_name": mapping.get("full_name", "N/A"),
                "timestamp": mapping.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "text": mapping.get("text", "O'chirilgan xabar"),
                "chat_id": mapping.get("chat_id", "N/A")
            }
            
            self._deleted_messages.append(deleted_data)
            self._safe_db_set("deleted_messages", self._deleted_messages)
            
        except Exception as e:
            try:
                channel_id = self.config["CHANNEL_ID"]
                if channel_id:
                    err_txt = "".join(traceback.format_exception_only(type(e), e)).strip()
                    await self._send_error_to_channel(
                        channel_id, 
                        None, 
                        "Add to deleted list error", 
                        err_txt, 
                        context="add_deleted"
                    )
            except Exception:
                pass