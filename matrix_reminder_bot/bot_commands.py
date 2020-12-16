import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import dateparser
import pytz
from apscheduler.job import Job
from nio import AsyncClient, MatrixRoom
from nio.events.room_events import RoomMessageText
from readabledelta import readabledelta

from matrix_reminder_bot.config import CONFIG
from matrix_reminder_bot.errors import CommandError, CommandSyntaxError
from matrix_reminder_bot.functions import command_syntax, \
    cache_http_download, send_text_to_room, send_image_to_room
from matrix_reminder_bot.reminder import ALARMS, REMINDERS, SCHEDULER, Reminder
from matrix_reminder_bot.storage import Storage

from mtgsdk import Card

logger = logging.getLogger(__name__)

class Command(object):
    def __init__(
        self,
        client: AsyncClient,
        store: Storage,
        command: str,
        room: MatrixRoom,
        event: RoomMessageText,
    ):
        """A command made by a user

        Args:
            client: The client to communicate to matrix with
            store: Bot storage
            command: The command and arguments
            room: The room the command was sent in
            event: The event describing the command
        """
        self.client = client
        self.store = store
        self.room = room
        self.event = event

        msg_without_prefix = command[
            len(CONFIG.command_prefix) :
        ]  # Remove the cmd prefix
        self.args = (
            msg_without_prefix.split()
        )  # Get a list of all items, split by spaces
        self.command = self.args.pop(
            0
        )  # Remove the first item and save as the command (ex. `remindme`)

    async def process(self):
        """Process the command"""
        if self.command == "card":
            await self._card()
        elif self.command == "help":
            await self._help()

    @command_syntax("NAME")
    async def _card(self):
        name = " ".join(self.args)
        cards = Card.where(name=name).all()
        if not len(cards):
            text = f"Sorry, I couldn't find a card called {name}"
            await send_text_to_room(self.client, self.room.room_id, text)
        else:
            for c in cards:
                if c.image_url:
                    card = c
                    img_path = await cache_http_download(card.image_url)
                    await send_image_to_room(self.client, self.room.room_id, img_path)
                    break
            else:
                text = f"Huh, I couldn't find an image for {name}"
                await send_text_to_room(self.client, self.room.room_id, text)

    @command_syntax("")
    async def _help(self):
        """Show the help text"""
        # Ensure we don't tell the user to use something other than their configured command
        # prefix
        c = CONFIG.command_prefix

        if not self.args:
            text = (
                f"Hello, I am a bot! Use `{c}help TOPIC` "
                f"to view available commands. Available topics: card"
            )
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        topic = self.args[0]

        # Simply way to check for plurals
        if topic.startswith("card"):
            text = f"""
**Card**

Search for Magic: The Gatering cards, by name

```
{c}card NAME
```

"""
        else:
            # Unknown help topic
            return

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        """Computer says 'no'."""
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown help topic '{self.command}'. Try the 'help' command for more "
            f"information.",
        )
