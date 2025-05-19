# VenomX/utils/stream/queue.py

import os
from typing import Union

from VenomX import LOGGER
from config import autoclean, chatstats, userstats
from config.config import time_to_seconds
from VenomX.misc import db


async def put_queue(
    chat_id,
    original_chat_id,
    file,
    title,
    duration,
    user,
    vidid,
    user_id,
    stream,
    url: str = None,
    forceplay: Union[bool, str] = None,
):
    """
    Add a media item to the playback queue for a chat.
    
    Args:
        chat_id: ID of the chat where the media is queued.
        original_chat_id: ID of the chat where the command was issued.
        file: Path or identifier of the media file.
        title: Title of the media.
        duration: Duration of the media (e.g., "04:30").
        user: Name of the user who requested the media.
        vidid: Video ID (e.g., YouTube ID, "Telegram", "Soundcloud").
        user_id: ID of the user who requested the media.
        stream: Stream type (e.g., "video", "audio").
        url: Optional URL of the media (e.g., for JioSaavn).
        forceplay: If True, insert at the start of the queue.
    """
    title = title.title()
    try:
        duration_in_seconds = time_to_seconds(duration) - 3
    except Exception as e:
        LOGGER(__name__).warning(f"Error converting duration '{duration}' for chat {chat_id}: {str(e)}")
        duration_in_seconds = 0

    # Validate file path
    if file and isinstance(file, str) and os.path.exists(file):
        autoclean.append(file)
        LOGGER(__name__).debug(f"Added file {file} to autoclean for chat {chat_id}")
    elif file:
        LOGGER(__name__).warning(f"Invalid or non-existent file {file} for chat {chat_id}")

    put = {
        "title": title,
        "dur": duration,
        "streamtype": stream,
        "by": user,
        "chat_id": original_chat_id,
        "file": file,
        "vidid": vidid,
        "seconds": duration_in_seconds,
        "played": 0,
        "url": url,
    }

    # Initialize queue if not exists
    if chat_id not in db:
        db[chat_id] = []
        LOGGER(__name__).info(f"Initialized queue for chat {chat_id}")

    if forceplay:
        if check := db.get(chat_id):
            check.insert(0, put)
            LOGGER(__name__).info(f"Inserted {title} at start of queue for chat {chat_id} (forceplay)")
        else:
            db[chat_id].append(put)
            LOGGER(__name__).info(f"Started queue with {title} for chat {chat_id} (forceplay)")
    else:
        db[chat_id].append(put)
        LOGGER(__name__).info(f"Appended {title} to queue for chat {chat_id}")

    # Normalize vidid for statistics
    vidid = "Telegram" if vidid in ["Soundcloud"] or "Saavn" in vidid else vidid
    to_append = {"vidid": vidid, "title": title}

    # Update chat statistics
    try:
        if chat_id not in chatstats:
            chatstats[chat_id] = []
        chatstats[chat_id].append(to_append)
        LOGGER(__name__).debug(f"Updated chatstats for chat {chat_id} with {title}")
    except Exception as e:
        LOGGER(__name__).error(f"Error updating chatstats for chat {chat_id}: {str(e)}", exc_info=True)

    # Update user statistics
    try:
        if user_id not in userstats:
            userstats[user_id] = []
        userstats[user_id].append(to_append)
        LOGGER(__name__).debug(f"Updated userstats for user {user_id} with {title}")
    except Exception as e:
        LOGGER(__name__).error(f"Error updating userstats for user {user_id}: {str(e)}", exc_info=True)

    return


async def put_queue_index(
    chat_id,
    original_chat_id,
    file,
    title,
    duration,
    user,
    vidid,
    stream,
    forceplay: Union[bool, str] = None,
):
    """
    Add an index-based stream (e.g., M3U8, URL) to the playback queue.
    
    Args:
        chat_id: ID of the chat where the stream is queued.
        original_chat_id: ID of the chat where the command was issued.
        file: Stream identifier (e.g., URL).
        title: Title of the stream.
        duration: Duration of the stream (e.g., "URL stream").
        user: Name of the user who requested the stream.
        vidid: Stream ID (e.g., "index_url").
        stream: Stream type (e.g., "video", "audio").
        forceplay: If True, insert at the start of the queue.
    """
    put = {
        "title": title,
        "dur": duration,
        "streamtype": stream,
        "by": user,
        "chat_id": original_chat_id,
        "file": file,
        "vidid": vidid,
        "seconds": 0,
        "played": 0,
    }

    # Initialize queue if not exists
    if chat_id not in db:
        db[chat_id] = []
        LOGGER(__name__).info(f"Initialized queue for chat {chat_id}")

    if forceplay:
        if check := db.get(chat_id):
            check.insert(0, put)
            LOGGER(__name__).info(f"Inserted {title} at start of queue for chat {chat_id} (forceplay)")
        else:
            db[chat_id].append(put)
            LOGGER(__name__).info(f"Started queue with {title} for chat {chat_id} (forceplay)")
    else:
        db[chat_id].append(put)
        LOGGER(__name__).info(f"Appended {title} to queue for chat {chat_id}")

    return
