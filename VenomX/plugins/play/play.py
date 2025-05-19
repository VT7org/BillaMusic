# VenomX/plugins/play/play.py

import random
import string
import logging

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message

import config
from config import BANNED_USERS, lyrical
from strings import command
from VenomX import app, LOGGER, YouTube, Telegram, Resso, Spotify, JioSavan, Soundcloud, Apple
from VenomX.utils import seconds_to_min, time_to_seconds
from VenomX.utils.database import is_video_allowed
from VenomX.utils.decorators.play import PlayWrapper
from VenomX.utils.formatters import formats
from VenomX.utils.inline.play import (
    livestream_markup,
    playlist_markup,
    slider_markup,
    track_markup,
)
from VenomX.utils.inline.playlist import botplaylist_markup
from VenomX.utils.logger import play_logs
from VenomX.utils.stream.stream import stream

# Set up logging
logger = logging.getLogger(__name__)

@app.on_message(
    command(
        "PLAY_COMMAND",
        prefixes=["/", "!", "%", ",", "@", "#"],
    )
    & filters.group
    & ~BANNED_USERS
)
@PlayWrapper
async def play_commnd(
    client,
    message: Message,
    _,
    chat_id,
    video,
    channel,
    playmode,
    url,
    fplay,
):
    try:
        mystic = await message.reply_text(
            _["play_2"].format(channel) if channel else _["play_1"]
        )
    except Exception as e:
        logger.error(f"Failed to send initial reply: {str(e)}", exc_info=True)
        return

    plist_id = None
    slider = None
    plist_type = None
    spotify = None
    user_id = message.from_user.id
    user_name = message.from_user.mention
    audio_telegram = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    video_telegram = (
        (message.reply_to_message.video or message.reply_to_message.document)
        if message.reply_to_message
        else None
    )
    if audio_telegram:
        if audio_telegram.file_size > config.TG_AUDIO_FILESIZE_LIMIT:
            await mystic.edit_text(_["play_5"])
            return
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, duration_min)
            )
            return
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }

            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    err = _["general_3"].format(ex_type)
                    logger.error(f"Stream error for Telegram audio: {str(e)}", exc_info=True)
                await mystic.edit_text(err)
            await mystic.delete()
            return
    elif video_telegram:
        if not await is_video_allowed(message.chat.id):
            await mystic.edit_text(_["play_3"])
            return
        if message.reply_to_message.document:
            try:
                ext = video_telegram.file_name.split(".")[-1]
                if ext.lower() not in formats:
                    await mystic.edit_text(
                        _["play_8"].format(f"{' | '.join(formats)}")
                    )
                    return
            except Exception:
                await mystic.edit_text(
                    _["play_8"].format(f"{' | '.join(formats)}")
                )
                return
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            await mystic.edit_text(_["play_9"])
            return
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram)
            dur = await Telegram.get_duration(video_telegram)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=True,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    logger.error(f"Stream error for Telegram video: {str(e)}", exc_info=True)
                    err = _["general_3"].format(ex_type)
                await mystic.edit_text(err)
            await mystic.delete()
            return
    elif url:
        if await YouTube.exists(url):
            if "playlist" in url:
                try:
                    details = await YouTube.playlist(
                        url,
                        config.PLAYLIST_FETCH_LIMIT,
                    )
                except Exception as e:
                    logger.error(f"YouTube playlist error: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "Yt_playlist"
                plist_type = "yt"
                if "&" in url:
                    plist_id = (url.split("=")[1]).split("&")[0]
                else:
                    plist_id = url.split("=")[1]
                img = config.PLAYLIST_IMG_URL
                cap = _["play_10"]
            elif "https://youtu.be" in url:
                videoid = url.split("/")[-1].split("?")[0]
                try:
                    details, track_id = await YouTube.track(
                        f"https://www.youtube.com/watch?v={videoid}"
                    )
                except Exception as e:
                    logger.error(f"YouTube track error: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(
                    details["title"],
                    details["duration_min"],
                )
            else:
                try:
                    details, track_id = await YouTube.track(url)
                except Exception as e:
                    logger.error(f"YouTube track error: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(
                    details["title"],
                    details["duration_min"],
                )
        elif await Spotify.valid(url):
            spotify = True
            if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET:
                await mystic.edit_text(
                    "This Bot can't play spotify tracks and playlist, please contact my owner and ask him to add Spotify player."
                )
                return
            if "track" in url:
                try:
                    details, track_id = await Spotify.track(url)
                except Exception:
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "Spotify"
                img = details["thumb"]
                cap = _["play_11"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                try:
                    details, plist_id = await Spotify.playlist(url)
                except Exception:
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "Spotify-Playlist"
                plist_type = "spplay"
                img = config.SPOTIFY_PLAYLIST_IMG_URL
                cap = _["play_12"].format(message.from_user.first_name)
            elif "album" in url:
                try:
                    details, plist_id = await Spotify.album(url)
                except Exception:
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "Spoti-Album"
                plist_type = "spalbum"
                img = config.SPOTIFY_ALBUM_IMG_URL
                cap = _["play_12"].format(message.from_user.first_name)
            elif "artist" in url:
                try:
                    details, plist_id = await Spotify.artist(url)
                except Exception:
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "Spoti-Artist"
                plist_type = "spartist"
                img = config.SPOTIFY_ARTIST_IMG_URL
                cap = _["play_12"].format(message.from_user.first_name)
            else:
                await mystic.edit_text(_["play_17"])
                return
        elif await Apple.valid(url):
            if "album" in url:
                try:
                    details, track_id = await Apple.track(url)
                except Exception:
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "Apple-Music"
                img = details["thumb"]
                cap = _["play_11"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True
                try:
                    details, plist_id = await Apple.playlist(url)
                except Exception:
                    await mystic.edit_text(_["play_3"])
                    return
                streamtype = "Apple-playlist"
                plist_type = "apple"
                cap = _["play_13"].format(message.from_user.first_name)
                img = url
            else:
                await mystic.edit_text(_["play_16"])
                return
        elif await Resso.valid(url):
            try:
                details, track_id = await Resso.track(url)
            except Exception:
                await mystic.edit_text(_["play_3"])
                return
            streamtype = "Resso"
            img = details["thumb"]
            cap = _["play_11"].format(details["title"], details["duration_min"])
        elif await JioSavan.valid(url):
            if "shows" in url:
                await mystic.edit_text(_["saavn_1"])
                return
            elif await JioSavan.is_song(url):
                try:
                    file_path, details = await JioSavan.download(url)
                except Exception as e:
                    ex_type = type(e).__name__
                    logger.error(f"JioSavan download error: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["play_3"])
                    return
                duration_sec = details["duration_sec"]
                streamtype = "saavn_track"
                if duration_sec > config.DURATION_LIMIT:
                    await mystic.edit_text(
                        _["play_6"].format(
                            config.DURATION_LIMIT_MIN,
                            details["duration_min"],
                        )
                    )
                    return
            elif await JioSavan.is_playlist(url):
                try:
                    details = await JioSavan.playlist(
                        url, limit=config.PLAYLIST_FETCH_LIMIT
                    )
                    streamtype = "JioSavn_playlist"
                except Exception as e:
                    ex_type = type(e).__name__
                    logger.error(f"JioSavan playlist error: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["play_3"])
                    return
                if len(details) == 0:
                    await mystic.edit_text(_["play_3"])
                    return
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype=streamtype,
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    err = _["general_3"].format(ex_type)
                    logger.error(f"Stream error for JioSavan: {str(e)}", exc_info=True)
                await mystic.edit_text(err)
            await mystic.delete()
            return
        elif await Soundcloud.valid(url):
            try:
                details, track_path = await Soundcloud.download(url)
            except Exception:
                await mystic.edit_text(_["play_3"])
                return
            duration_sec = details["duration_sec"]
            if duration_sec > config.DURATION_LIMIT:
                await mystic.edit_text(
                    _["play_6"].format(
                        config.DURATION_LIMIT_MIN,
                        details["duration_min"],
                    )
                )
                return
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="Soundcloud",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    logger.error(f"Stream error for Soundcloud: {str(e)}", exc_info=True)
                    err = _["general_3"].format(ex_type)
                await mystic.edit_text(err)
            await mystic.delete()
            return
        else:
            if not await Telegram.is_streamable_url(url):
                await mystic.edit_text(_["play_19"])
                return
            await mystic.edit_text(_["str_2"])
            try:
                await stream(
                    _,
                    mystic,
                    message.from_user.id,
                    url,
                    chat_id,
                    message.from_user.first_name,
                    message.chat.id,
                    video=video,
                    streamtype="index",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    logger.error(f"Stream error for URL: {str(e)}", exc_info=True)
                    err = _["general_3"].format(ex_type)
                await mystic.edit_text(err)
            await play_logs(message, streamtype="M3u8 or Index Link")
            return
    else:
        if len(message.command) < 2:
            buttons = botplaylist_markup(_)
            await mystic.edit_text(
                _["playlist_1"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return
        slider = True
        query = message.text.split(None, 1)[1]
        logger.info(f"Processing search query: {query}")
        if "-v" in query:
            query = query.replace("-v", "")
        try:
            details, track_id = await YouTube.track(query)
            logger.info(f"YouTube search result: {details}, track_id: {track_id}")
        except ValueError as ve:
            logger.warning(f"No YouTube search results for query: {query}")
            await mystic.edit_text("No results found for your query.")
            return
        except Exception as e:
            logger.error(f"YouTube search error for query {query}: {str(e)}", exc_info=True)
            await mystic.edit_text(_["play_3"])
            return
        streamtype = "Youtube"
    if str(playmode) == "Direct" and not plist_type:
        if details["duration_min"]:
            duration_sec = time_to_seconds(details["duration_min"])
            if duration_sec > config.DURATION_LIMIT:
                await mystic.edit_text(
                    _["play_6"].format(
                        config.DURATION_LIMIT_MIN,
                        details["duration_min"],
                    )
                )
                return
        else:
            buttons = livestream_markup(
                _,
                track_id,
                user_id,
                "v" if video else "a",
                "c" if channel else "g",
                "f" if fplay else "d",
            )
            await mystic.edit_text(
                _["play_15"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return
        try:
            await stream(
                _

,
                mystic,
                user_id,
                details,
                chat_id,
                user_name,
                message.chat.id,
                video=video,
                streamtype=streamtype,
                spotify=spotify,
                forceplay=fplay,
            )
        except Exception as e:
            ex_type = type(e).__name__
            if ex_type == "AssistantErr":
                err = e
            else:
                logger.error(f"Stream error for YouTube: {str(e)}", exc_info=True)
                err = _["general_3"].format(ex_type)
            await mystic.edit_text(err)
        await mystic.delete()
        await play_logs(message, streamtype=streamtype)
        return
else:
        if plist_type:
            ran_hash = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )
            lyrical[ran_hash] = plist_id
            buttons = playlist_markup(
                _,
                ran_hash,
                message.from_user.id,
                plist_type,
                "c" if channel else "g",
                "f" if fplay else "d",
            )
            await mystic.delete()
            await message.reply_photo(
                photo=img,
                caption=cap,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            await play_logs(message, streamtype=f"Playlist : {plist_type}")
            return
        else:
            if slider:
                buttons = slider_markup(
                    _,
                    track_id,
                    message.from_user.id,
                    query,
                    0,
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                try:
                    await mystic.delete()
                    await message.reply_photo(
                        photo=details["thumb"],
                        caption=_["play_11"].format(details["title"], details["duration_min"]),
                        reply_markup=InlineKeyboardMarkup(buttons),
                    )
                except Exception as e:
                    logger.error(f"Error sending slider reply: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["general_3"].format(type(e).__name__))
                    return
