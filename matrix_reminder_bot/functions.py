import logging
from typing import Callable, Optional

from markdown import markdown
import aiohttp
import aiofiles
import aiofiles.os
import hashlib
import os.path
import mimetypes
from nio import AsyncClient, SendRetryError, LoginResponse, UploadResponse

from matrix_reminder_bot.config import CONFIG
from matrix_reminder_bot.errors import CommandSyntaxError
import magic as file_type_finder
from PIL import Image
from mtgsdk import Card

logger = logging.getLogger(__name__)
URL_CACHE_DIR="/data/url_cache"
MTG_CACHE_DIR="/data/mtg_cache"

# async def mtg_card_cache(name: str):
#     directory = os.path.join(MTG_CACHE_DIR, 'cards')
#     path = os.path.join(directory, f'{name}.json')
#     if os.path.exists(path):
#         return path
#     os.makedirs(directory, exist_ok=True)

#     cards = Card.where(name=name).all()
#     if not len(cards):
#         text = f"Sorry, I couldn't find a card called {name}"
#         await send_text_to_room(self.client, self.room.room_id, text)
#     else:
#         for c in cards:
#             if c.image_url:
#                 card = c
#                 img_path = await cache_http_download(card.image_url)
#                 await send_image_to_room(self.client, self.room.room_id, img_path)
#                 break
#         else:
#             text = f"Huh, I couldn't find an image for {name}"
#             await send_text_to_room(self.client, self.room.room_id, text)


async def http_download(url: str, path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(path, mode='wb')
                await f.write(await resp.read())
                await f.close()
                return path
            raise RuntimeError(f"Bad HTTP response ({resp.status}) for url: {url}")

async def cache_http_download(url):
    """Download URL to a file, and cache for the future"""
    hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    directory = os.path.join(URL_CACHE_DIR, hash[:2], hash[2:4])
    path = os.path.join(directory, hash)
    if os.path.exists(path):
        return path
    os.makedirs(directory, exist_ok=True)
    return await http_download(url, path)


async def send_image_to_room(
    client: AsyncClient,
    room_id: str,
    image: str):
    """Send image to room.

    Arguments:
    ---------
    client : Client
    room_id : str
    image : str, file name of image

    This is a working example for a JPG image.
        "content": {
            "body": "someimage.jpg",
            "info": {
                "size": 5420,
                "mimetype": "image/jpeg",
                "thumbnail_info": {
                    "w": 100,
                    "h": 100,
                    "mimetype": "image/jpeg",
                    "size": 2106
                },
                "w": 100,
                "h": 100,
                "thumbnail_url": "mxc://example.com/SomeStrangeThumbnailUriKey"
            },
            "msgtype": "m.image",
            "url": "mxc://example.com/SomeStrangeUriKey"
        }

    """
    mime_type = file_type_finder.from_file(image, mime=True)  # e.g. "image/jpeg"
    if not mime_type.startswith("image/"):
        print("Drop message because file does not have an image mime type.")
        return
    file_extension = mimetypes.guess_extension(mime_type) or ''

    im = Image.open(image)
    (width, height) = im.size  # im.size returns (width,height) tuple

    # first do an upload of image, then send URI of upload to room
    file_stat = await aiofiles.os.stat(image)
    async with aiofiles.open(image, "r+b") as f:
        resp, maybe_keys = await client.upload(
            f,
            content_type=mime_type,  # image/jpeg
            filename=f"{os.path.basename(image)}{file_extension}",
            filesize=file_stat.st_size)
    if (isinstance(resp, UploadResponse)):
        print("Image was uploaded successfully to server. ")
    else:
        print(f"Failed to upload image. Failure response: {resp}")

    content = {
        "body": os.path.basename(image),  # descriptive title
        "info": {
            "size": file_stat.st_size,
            "mimetype": mime_type,
            "thumbnail_info": None,  # TODO
            "w": width,  # width in pixel
            "h": height,  # height in pixel
            "thumbnail_url": None,  # TODO
        },
        "msgtype": "m.image",
        "url": resp.content_uri,
    }

    try:
        await client.room_send(
            room_id,
            message_type="m.room.message",
            content=content
        )
        print("Image was sent successfully")
    except Exception:
        print(f"Image send of file {image} failed.")

async def send_text_to_room(
    client: AsyncClient,
    room_id: str,
    message: str,
    notice: bool = True,
    markdown_convert: bool = True,
    reply_to_event_id: Optional[str] = None,
):
    """Send text to a matrix room.

    Args:
        client: The client to communicate to matrix with.

        room_id: The ID of the room to send the message to.

        message: The message content.

        notice: Whether the message should be sent with an "m.notice" message type
            (will not ping users).

        markdown_convert: Whether to convert the message content to markdown.
            Defaults to true.

        reply_to_event_id: Whether this message is a reply to another event. The event
            ID this is message is a reply to.
    """
    # Determine whether to ping room members or not
    msgtype = "m.notice" if notice else "m.text"

    content = {
        "msgtype": msgtype,
        "format": "org.matrix.custom.html",
        "body": message,
    }

    if markdown_convert:
        content["formatted_body"] = markdown(message)

    if reply_to_event_id:
        content["m.relates_to"] = {"m.in_reply_to": {"event_id": reply_to_event_id}}

    try:
        await client.room_send(
            room_id, "m.room.message", content, ignore_unverified_devices=True,
        )
    except SendRetryError:
        logger.exception(f"Unable to send message response to {room_id}")


def command_syntax(syntax: str):
    """Defines the syntax for a function, and informs the user if it is violated

    This function is intended to be used as a decorator, allowing command-handler
    functions to define the syntax that the user is supposed to use for the
    command arguments.

    The command function, passed to `outer`, can signal that this syntax has been
    violated by raising a CommandSyntaxError exception. This will then catch that
    exception and inform the user of the correct syntax for that command.

    Args:
        syntax: The syntax for the command that the user should follow
    """

    def outer(command_func: Callable):
        async def inner(self, *args, **kwargs):
            try:
                # Attempt to execute the command function
                await command_func(self, *args, **kwargs)
            except CommandSyntaxError:
                # The function indicated that there was a command syntax error
                # Inform the user of the correct syntax
                #
                # Grab the bot's configured command prefix, and the current
                # command's name from the `self` object passed to the command
                text = (
                    f"Invalid syntax. Please use "
                    f"`{CONFIG.command_prefix}{self.command} {syntax}`."
                )
                await send_text_to_room(self.client, self.room.room_id, text)

        return inner

    return outer
