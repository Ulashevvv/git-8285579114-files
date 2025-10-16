from .. import loader, utils
import aiohttp
import asyncio
import os
import zipfile
import re
import ssl
import time
from itertools import cycle
from urllib.parse import urljoin, urlparse
from pathlib import Path

@loader.tds
class FrontGrabberMod(loader.Module):
    """Sayt frontend qismini maksimal yuklab zip qiladi
    📌 Developer: @reewi"""
    strings = {"name": "FrontGrabber"}

    async def frontcmd(self, message):
        """Sayt frontendini zip qilish (crawl) | .front <url> [max_pages]
        📌 Developer: @reewi"""
        args = utils.get_args_raw(message).split()
        if not args:
            return await message.edit(
                "<emoji document_id=5346066456142429527>📱</emoji> Iltimos, URL manzil kiriting.\n"
                "Misol: `.front https://example.com 50`\n\n"
                "<emoji document_id=5346066456142429527>📱</emoji> Developer: @reewi"
            )

        base_url = args[0].strip()
        max_pages = int(args[1]) if len(args) > 1 and args[1].isdigit() else 30

        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = "http://" + base_url
            parsed = urlparse(base_url)

        if not parsed.netloc:
            return await message.edit("<emoji document_id=5346066456142429527>📱</emoji> Noto'g'ri URL format\n\n<emoji document_id=5346066456142429527>📱</emoji> Developer: @reewi")

        site_name = parsed.netloc.replace("www.", "").split(".")[0]
        if not site_name:
            site_name = "site"
        zip_filename = f"{site_name}.zip"

        await message.edit(
            f"<emoji document_id=5873204392429096339>⌨</emoji> Sayt yuklab olinmoqda...\n"
            f"<emoji document_id=5346066456142429527>📱</emoji> URL: {base_url}\n"
            f"<emoji document_id=5346066456142429527>📱</emoji> Limit: {max_pages} ta sahifa\n"
            f"<emoji document_id=5346066456142429527>📱</emoji> Fayl: {zip_filename}\n\n"
            f"<emoji document_id=5346066456142429527>📱</emoji> Developer: @reewi"
        )

        folder = "site_download"
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(folder)
        
        os.makedirs(folder)

        subfolders = {
            "css": os.path.join(folder, "css"),
            "js": os.path.join(folder, "js"),
            "img": os.path.join(folder, "img"),
            "other": os.path.join(folder, "other"),
        }
        for sub in subfolders.values():
            os.makedirs(sub, exist_ok=True)

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        visited = set()
        queue = [base_url]
        downloaded_files = set()
        start_time = time.time()

        # Cycle uchun premium emojilar
        sahifa_emojis = cycle([
            "<emoji document_id=5332627207120501692>🔆</emoji>",
            "<emoji document_id=5332541217580271110>🔄</emoji>",
            "<emoji document_id=5332745426095325225>💫</emoji>",
        ])

        def progress_bar(current, total, length=15):
            if total == 0:
                return "░" * length
            filled = int(length * current / total)
            return "█" * filled + "░" * (length - filled)

        def sanitize_filename(filename):
            return re.sub(r'[<>:"/\\|?*]', '_', filename)

        def get_unique_filename(directory, filename):
            path = Path(directory) / filename
            if not path.exists():
                return str(path)
            
            stem = path.stem
            suffix = path.suffix
            counter = 1
            while True:
                new_name = f"{stem}_{counter}{suffix}"
                new_path = Path(directory) / new_name
                if not new_path.exists():
                    return str(new_path)
                counter += 1

        try:
            timeout = aiohttp.ClientTimeout(total=20)
            connector = aiohttp.TCPConnector(limit=15, ssl=ssl_context)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:

                async def fetch_page(url):
                    try:
                        async with session.get(url, allow_redirects=True) as resp:
                            if resp.status != 200 or "text/html" not in resp.headers.get("content-type", "").lower():
                                return None, None
                            content = await resp.read()
                            try:
                                html = content.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    html = content.decode('latin-1')
                                except UnicodeDecodeError:
                                    return None, None
                            return html, str(resp.url)
                    except Exception:
                        return None, None

                async def fetch_file(file_url, referer):
                    abs_url = urljoin(referer, file_url)
                    if abs_url in downloaded_files:
                        return
                    
                    try:
                        async with session.get(abs_url) as resp:
                            if resp.status == 200:
                                content = await resp.read()
                                if not content:
                                    return
                                
                                parsed_file = urlparse(file_url)
                                file_path = parsed_file.path
                                if not file_path or file_path == "/":
                                    return
                                
                                filename = os.path.basename(file_path)
                                if not filename:
                                    return
                                
                                filename = sanitize_filename(filename.split("?")[0])
                                if not filename:
                                    return
                                
                                ext = os.path.splitext(filename)[1].lower()
                                if ext in [".css"]:
                                    folder_path = subfolders["css"]
                                elif ext in [".js"]:
                                    folder_path = subfolders["js"]
                                elif ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp", ".tiff"]:
                                    folder_path = subfolders["img"]
                                else:
                                    folder_path = subfolders["other"]
                                
                                file_path = get_unique_filename(folder_path, filename)
                                
                                with open(file_path, "wb") as f:
                                    f.write(content)
                                downloaded_files.add(abs_url)
                    except Exception:
                        pass

                while queue and len(visited) < max_pages:
                    current_batch_size = min(5, len(queue), max_pages - len(visited))
                    batch = []
                    
                    for _ in range(current_batch_size):
                        if queue:
                            link = queue.pop(0)
                            if link not in visited:
                                visited.add(link)
                                batch.append(fetch_page(link))

                    if not batch:
                        break

                    results = await asyncio.gather(*batch)
                    file_tasks = []
                    new_links = []

                    for html, url in results:
                        if not html or not url:
                            continue

                        parsed_url = urlparse(url)
                        path = parsed_url.path
                        if not path or path == "/":
                            filename = "index.html"
                        else:
                            filename = os.path.basename(path)
                            if not filename or "." not in filename:
                                filename = f"page_{len(visited)}.html"
                            else:
                                name, ext = os.path.splitext(filename)
                                if not ext or ext not in [".html", ".htm", ".php", ".asp", ".aspx"]:
                                    filename = f"{name}.html"
                        
                        filename = sanitize_filename(filename)
                        html_path = os.path.join(folder, filename)
                        html_path = get_unique_filename(folder, filename)
                        
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(html)

                        resource_patterns = [
                            r'src="(.*?)"',
                            r'href="(.*?)"',
                            r"src='(.*?)'",
                            r"href='(.*?)'",
                            r'url\(\s*[\'"]?(.*?)[\'"]?\s*\)'
                        ]
                        
                        all_resources = []
                        for pattern in resource_patterns:
                            matches = re.findall(pattern, html, re.IGNORECASE)
                            all_resources.extend(matches)
                        
                        for resource in all_resources:
                            if not resource or resource.startswith(('#', 'mailto:', 'javascript:', 'data:')):
                                continue
                            file_tasks.append(fetch_file(resource, url))

                        link_pattern = r'href="([^"]*)"'
                        links = re.findall(link_pattern, html, re.IGNORECASE)
                        
                        for link in links:
                            if not link or link.startswith(('#', 'mailto:', 'javascript:', 'tel:')):
                                continue
                            
                            abs_link = urljoin(url, link)
                            parsed_link = urlparse(abs_link)
                            
                            if (parsed_link.netloc == parsed.netloc and 
                                abs_link not in visited and 
                                abs_link not in queue and
                                abs_link not in new_links and
                                len(visited) + len(queue) + len(new_links) < max_pages):
                                new_links.append(abs_link)

                    queue.extend(new_links)

                    if file_tasks:
                        await asyncio.gather(*file_tasks)

                    # --- Animatsion sahifa emoji
                    sahifa_emoji = next(sahifa_emojis)

                    elapsed = time.time() - start_time
                    processed = len(visited)
                    if processed > 0:
                        avg_time = elapsed / processed
                        remaining = max_pages - processed
                        eta = int(avg_time * remaining)
                        mins, secs = divmod(eta, 60)
                        bar = progress_bar(processed, max_pages)
                        percentage = int(processed / max_pages * 100) if max_pages > 0 else 0
                        
                        status_msg = (
                            f"<emoji document_id=5873204392429096339>⌨</emoji> Yuklanmoqda...\n"
                            f"<emoji document_id=5346066456142429527>📱</emoji> Sahifalar {sahifa_emoji}: {processed}/{max_pages}\n"
                            f"{bar} {percentage}%\n"
                            f"<emoji document_id=5346066456142429527>📱</emoji> Fayllar: {len(downloaded_files)}\n"
                            f"<emoji document_id=5346066456142429527>📱</emoji> Qolgan vaqt: {mins}m {secs}s\n\n"
                            f"<emoji document_id=5346066456142429527>📱</emoji> Developer: @reewi"
                        )
                        await message.edit(status_msg)

                    await asyncio.sleep(0.7)

            with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder)
                        zipf.write(file_path, arcname)

            await message.client.send_file(
                message.chat_id,
                zip_filename,
                caption=(
                    f"<emoji document_id=5346066456142429527>📱</emoji> Sayt frontend muvaffaqiyatli yuklandi!\n"
                    f"<emoji document_id=5346066456142429527>📱</emoji> Sait: {parsed.netloc}\n"
                    f"<emoji document_id=5346066456142429527>📱</emoji> Sahifalar: {len(visited)}\n"
                    f"<emoji document_id=5346066456142429527>📱</emoji> Fayllar: {len(downloaded_files)}\n"
                    f"<emoji document_id=5346066456142429527>📱</emoji> Arxiv: {zip_filename}\n\n"
                    f"<emoji document_id=5346066456142429527>📱</emoji> Developer: @reewi"
                )
            )

        except Exception as e:
            await message.edit(f"<emoji document_id=5346066456142429527>📱</emoji> Xato yuz berdi: {str(e)}\n\n<emoji document_id=5346066456142429527>📱</emoji> Developer: @reewi")
        finally:
            try:
                if os.path.exists(folder):
                    for root, dirs, files in os.walk(folder, topdown=False):
                        for file in files:
                            os.remove(os.path.join(root, file))
                        for dir in dirs:
                            os.rmdir(os.path.join(root, dir))
                    os.rmdir(folder)
                
                if os.path.exists(zip_filename):
                    os.remove(zip_filename)
            except Exception:
                pass

        await message.delete()