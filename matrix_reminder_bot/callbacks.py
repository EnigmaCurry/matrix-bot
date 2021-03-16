import re
import logging
import emoji
import traceback

from nio import (
    AsyncClient,
    InviteMemberEvent,
    JoinError,
    MatrixRoom,
    MegolmEvent,
    RoomMessageText,
)

from matrix_reminder_bot.bot_commands import Command
from matrix_reminder_bot.config import CONFIG
from matrix_reminder_bot.errors import CommandError
from matrix_reminder_bot.functions import command_syntax, \
    cache_http_download, cache_http_get, send_text_to_room, \
    send_image_to_room
from matrix_reminder_bot.image import remove_transparency, thumbnail, svg_to_img
from matrix_reminder_bot.emoji_grid import emoji_grid
from matrix_reminder_bot.storage import Storage

import json
import random
import tempfile
from PIL import Image

import TheNounProjectAPI

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
import time
TIME_STARTUP = time.time() * 1000

from .api_keys import noun_project_api_key, noun_project_secret_key

class Callbacks(object):
    """Callback methods that fire on certain matrix events

    Args:
        client: nio client used to interact with matrix
        store: Bot storage
    """

    def __init__(self, client: AsyncClient, store: Storage):
        self.client = client
        import pprint
        self.store = store
        self.meme_regex = re.compile(":[^ ]+:[^ ]*")
        self.grid_regex = re.compile("^!(grid[a-zA-Z0-9]*)[ \n](.*)", re.DOTALL)
        self.username = CONFIG.user_id.lstrip("@").split(":")[0]
        self.mention_re = re.compile(f"^(.*\W)?{self.username}(\W.*)?$")
        self.greeting_re = re.compile(f"(.*\W)?([Hh]i|[Hh]ey|[Hh]ello|[Yy]o|[Gg]reetings|[Gg]ood morning|[Gg]ood afternoon|[Gg]ood night|[Hh]owdy)(\W.*)?$")
        print(self.client.user)

    async def message(self, room: MatrixRoom, event: RoomMessageText):
        """Callback for when a message event is received"""
        # Extract the formatted message text, or the basic text if no formatting is available
        msg = event.formatted_body or event.body
        if not msg:
            return

        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        ## Ignore messages from the past before the bot started
        if event.server_timestamp < TIME_STARTUP:
            return

        logger.debug(msg)

        ## Useful idioms:
        # command = Command(self.client, self.store, msg, room, event)
        # await send_text_to_room(self.client, room.room_id, msg)
        # logger.exception("Unknown error while processing command:")

        ## Greetings
        if self.mention_re.search(msg):
            greeting = self.greeting_re.search(msg)
            if greeting:
                await send_text_to_room(self.client, room.room_id, msg.replace(self.username, (await self.client.get_displayname(event.sender)).displayname))
                return

        ## Emoji Grid
        grid_m = self.grid_regex.match(msg)
        if grid_m:
            grid_variation, grid_args = grid_m.groups()
            grid_args = emoji.emojize(grid_args, use_aliases=True)
            emoji_list = [e['emoji'] for e in emoji.emoji_lis(grid_args)]
            try:
                grid = emoji_grid(grid_args, variation=grid_variation)
            except Exception as e:
                await send_text_to_room(self.client, room.room_id,
                                        str(e), markdown_convert=False)
                traceback.print_exc()
                return
            else:
                await send_text_to_room(self.client, room.room_id,
                                        grid,
                                        markdown_convert=False)
                return

        ## Memes
        for m in self.meme_regex.findall(msg):
            parts = m.split(":")[1:]
            term = parts[0].replace("_"," ")
            criteria = parts[1:]
            criteria.append("icon")
            ## Attempt several times to find an image
            backends = ["iconduck"]
            for attempt in range(1):
                try:
                    backend = random.choice(backends)
                    logger.debug(f"Querying {backend} with term: {term}")
                except IndexError:
                    logger.debug("Ran out of backends to try!")
                    break
                if backend == "iconduck":
                    result = json.loads(await cache_http_get(
                        f"https://iconduck.com/api/v1/vectors/search?query={term}&key=test"))
                    if len(result['objects']) == 0:
                        backends.remove("iconduck")
                        logger.debug(f"No results: {backend}")
                        continue
                    obj = random.choice(result['objects'])
                    img_path = await cache_http_download(obj['assets'][0]['url'])
                    if obj['contentType'].startswith('image/svg'):
                        try:
                            img = svg_to_img(img_path)
                        except TypeError:
                            if len(result['objects']) == 1:
                                backends.remove("iconduck")
                            logger.debug(f"Could not render SVG from {backend}")
                            continue
                        logger.debug(f"img: {img}")
                        img = remove_transparency(img)
                        img = thumbnail(img)
                        await send_image_to_room(self.client, room.room_id, img)
                        return
                    else:
                        logger.info(obj['contentType'])
                elif backend == "thenounproject":
                    api = TheNounProjectAPI.API(key=noun_project_api_key, secret=noun_project_secret_key)
                    try:
                        icons = api.get_icons_by_term(term, public_domain_only=False, limit=10)
                    except:
                        continue
                    if len(icons) == 0:
                        backends.remove("thenounproject")
                        continue
                    icon = random.choice(icons)
                    img_path = await cache_http_download(icon['preview_url'], f"{term}-noun")
                    img = Image.open(img_path)
                    logger.debug(f"img: {img}")
                    img = remove_transparency(img)
                    logger.debug(f"img: {img}")
                    img = thumbnail(img)
                    logger.debug(f"img: {img}")
                    await send_image_to_room(self.client, room.room_id, img)
                    return

    async def invite(self, room: MatrixRoom, event: InviteMemberEvent):
        """Callback for when an invite is received. Join the room specified in the invite"""
        logger.debug(f"Got invite to {room.room_id} from {event.sender}.")

        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await self.client.join(room.room_id)
            if type(result) == JoinError:
                logger.error(
                    f"Error joining room {room.room_id} (attempt %d): %s",
                    attempt,
                    result.message,
                )
            else:
                logger.info(f"Joined {room.room_id}")
                break

    async def decryption_failure(self, room: MatrixRoom, event: MegolmEvent):
        """Callback for when an event fails to decrypt. Inform the user"""
        ## Don't care about historical messages:
        if event.server_timestamp > TIME_STARTUP:
            logger.error(
                f"Failed to decrypt event '{event.event_id}' in room '{room.room_id}'!"
            )

            user_msg = (
                "Unable to decrypt this message. "
                "Check whether you've chosen to only encrypt to trusted devices."
            )
            await send_text_to_room(
                self.client, room.room_id, user_msg, reply_to_event_id=event.event_id,
            )
