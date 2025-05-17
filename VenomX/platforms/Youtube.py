# All rights reserved.
#
import asyncio
import os
import random
import re
import requests

from async_lru import alru_cache
from py_yt import VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from yt_dlp import YoutubeDL

import config
from VenomX.utils.database import is_on_off
from VenomX.utils.decorators import asyncify
from VenomX.utils.formatters import seconds_to_min, time_to_seconds

NOTHING = {"cookies_dead": None}

def extract_video_id(link: str) -> str:
    patterns = [
        r'youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/(?:playlist\?list=[^&]+&v=|v\/)([0-9A-Za-z_-]{11})',
        r'youtube\.com\/(?:.*\?v=|.*/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube link provided.")

def api_dl(video_id: str) -> str:
    api_url = f"https://spotify.ashlynn.workers.dev/arytmp3?direct&id={video_id}"
    file_path = os.path.join("downloads", f"{video_id}.mp3")
    if os.path.exists(file_path):
        return file_path
    try:
        with requests.get(api_url, stream=True) as response:
            if response.status_code == 200:
                os.makedirs("downloads", exist_ok=True)
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return file_path
            else:
                return None
    except requests.RequestException:
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


def cookies():
    folder_path = f"{os.getcwd()}/cookies"
    txt_files = [file for file in os.listdir(folder_path) if file.endswith(".txt")]
    if not txt_files:
        raise FileNotFoundError("No Cookies found in cookies directory.")
    return os.path.join(folder_path, random.choice(txt_files))

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz and "unavailable videos are hidden" not in errorz.decode().lower():
        return errorz.decode("utf-8")
    return out.decode("utf-8")

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    @property
    def use_fallback(self):
        return NOTHING["cookies_dead"] is True

    @use_fallback.setter
    def use_fallback(self, value):
        if NOTHING["cookies_dead"] is None:
            NOTHING["cookies_dead"] = value

    @asyncify
    def url(self, message_1: Message) -> str | None:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

@alru_cache(maxsize=None)
async def details(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0] if "&" in link else link
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    @alru_cache(maxsize=None)
    async def title(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0] if "&" in link else link
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["title"]

    @alru_cache(maxsize=None)
    async def duration(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0] if "&" in link else link
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["duration"]

    @alru_cache(maxsize=None)
    async def thumbnail(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0] if "&" in link else link
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0] if "&" in link else link
        cmd = [
            "yt-dlp",
            "--cookies", cookies(),
            "-g",
            "-f", "best[height<=?720][width<=?1280]",
            link,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

@alru_cache(maxsize=None)
    async def playlist(self, link, limit, videoid: bool | str = None):
        if videoid:
            link = self.listbase + link
        link = link.split("&")[0] if "&" in link else link

        cmd = (
            f"yt-dlp -i --compat-options no-youtube-unavailable-videos "
            f'--get-id --flat-playlist --playlist-end {limit} --skip-download "{link}" '
            f"2>/dev/null"
        )
        playlist = await shell_cmd(cmd)
        try:
            result = [key for key in playlist.split("\n") if key]
        except Exception:
            result = []
        return result

    @alru_cache(maxsize=None)
    async def track(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0] if "&" in link else link
        if link.startswith("http://") or link.startswith("https://"):
            return await self._track(link)
        try:
            results = VideosSearch(link, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration_min = result["duration"]
                vidid = result["id"]
                yturl = result["link"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            return {
                "title": title,
                "link": yturl,
                "vidid": vidid,
                "duration_min": duration_min,
                "thumb": thumbnail,
            }, vidid
        except Exception:
            return await self._track(link)

    @asyncify
    def _track(self, q):
        options = {
            "format": "best",
            "noplaylist": True,
            "quiet": True,
            "extract_flat": "in_playlist",
            "cookiefile": cookies(),
        }
        with YoutubeDL(options) as ydl:
            info_dict = ydl.extract_info(f"ytsearch:{q}", download=False)
            details = info_dict.get("entries")[0]
            return {
                "title": details["title"],
                "link": details["url"],
                "vidid": details["id"],
                "duration_min": (
                    seconds_to_min(details["duration"])
                    if details["duration"] != 0 else None
                ),
                "thumb": details["thumbnails"][0]["url"],
            }, details["id"]

@alru_cache(maxsize=None)
    @asyncify
    def formats(self, link: str, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0] if "&" in link else link

        ytdl_opts = {
            "quiet": True,
            "cookiefile": cookies(),
        }

        with YoutubeDL(ytdl_opts) as ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except Exception:
                    continue
                if "dash" not in str(format["format"]).lower():
                    try:
                        formats_available.append(
                            {
                                "format": format["format"],
                                "filesize": format["filesize"],
                                "format_id": format["format_id"],
                                "ext": format["ext"],
                                "format_note": format["format_note"],
                                "yturl": link,
                            }
                        )
                    except KeyError:
                        continue
        return formats_available, link

    @alru_cache(maxsize=None)
    async def slider(self, link: str, query_type: int, videoid: bool | str = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0] if "&" in link else link
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        data = result[query_type]
        return (
            data["title"],
            data["duration"],
            data["thumbnails"][0]["url"].split("?")[0],
            data["id"],
        )

async def download(
        self,
        link: str,
        mystic,
        video: bool | str = None,
        videoid: bool | str = None,
        songaudio: bool | str = None,
        songvideo: bool | str = None,
        format_id: bool | str = None,
        title: bool | str = None,
    ) -> str:
        if videoid:
            link = self.base + link

        @asyncify
        def audio_dl():
            ydl_optssx = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "cookiefile": cookies(),
                "prefer_ffmpeg": True,
            }

            with YoutubeDL(ydl_optssx) as x:
                info = x.extract_info(link, False)
                xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                if os.path.exists(xyz):
                    return xyz
                x.download([link])
                return xyz

        @asyncify
        def video_dl():
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "cookiefile": cookies(),
            }

            with YoutubeDL(ydl_optssx) as x:
                info = x.extract_info(link, False)
                xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                if os.path.exists(xyz):
                    return xyz
                x.download([link])
                return xyz

        @asyncify
        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_optssx = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
                "cookiefile": cookies(),
            }

            with YoutubeDL(ydl_optssx) as x:
                info = x.extract_info(link)
                return x.prepare_filename(info)

        @asyncify
        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_optssx = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "cookiefile": cookies(),
            }

            with YoutubeDL(ydl_optssx) as x:
                info = x.extract_info(link)
                return x.prepare_filename(info)

        if songvideo:
            return await song_video_dl()

        elif songaudio:
            return await song_audio_dl()

        elif video:
            if await is_on_off(config.YTDOWNLOADER):
                direct = True
                downloaded_file = await video_dl()
            else:
                command = [
                    "yt-dlp",
                    "--cookies", cookies(),
                    "-g",
                    "-f", "best",
                    link,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    downloaded_file = stdout.decode().split("\n")[0]
                    direct = None
                else:
                    downloaded_file = await video_dl()
                    direct = True
        else:
            direct = True
            downloaded_file = await audio_dl()

        return downloaded_file, direct


# Extra integration at bottom of file
import requests

def api_dl(video_id: str) -> str:
    api_url = f"https://spotify.ashlynn.workers.dev/arytmp3?direct&id={video_id}"
    file_path = os.path.join("downloads", f"{video_id}.mp3")

    if os.path.exists(file_path):
        print(f"{file_path} already exists. Skipping download.")
        return file_path

    try:
        with requests.get(api_url, stream=True) as response:
            if response.status_code == 200:
                os.makedirs("downloads", exist_ok=True)
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Downloaded {file_path}")
                return file_path
            else:
                print(f"Failed to download {video_id}. Status: {response.status_code}")
                return None
    except requests.RequestException as e:
        print(f"Error downloading {video_id}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


def extract_video_id(link: str) -> str:
    patterns = [
        r'youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/(?:playlist\?list=[^&]+&v=|v\/)([0-9A-Za-z_-]{11})',
        r'youtube\.com\/(?:.*\?v=|.*\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube link provided.")
