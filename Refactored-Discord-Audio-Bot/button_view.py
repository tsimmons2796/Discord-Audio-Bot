import logging
import uuid
import asyncio

from discord import ButtonStyle, Interaction, User
from discord.ui import Button, View
from typing import Optional
from queue_manager import queue_manager, QueueEntry
from utils import create_now_playing_embed, schedule_progress_bar_update
from view_functions import (
    handle_lyrics_button,
    handle_loop_button,
    handle_favorite_button,
    handle_pause_button,
    handle_resume_button,
    handle_stop_button,
    handle_skip_button,
    handle_restart_button,
    handle_shuffle_button,
    handle_list_queue_button,
    handle_remove_button,
    handle_previous_button,
    handle_move_up_button,
    handle_move_down_button,
    handle_move_to_top_button,
    handle_move_to_bottom_button
)

logging.basicConfig(level=logging.DEBUG, filename='views.log', format='%(asctime)s:%(levelname)s:%(message)s')


class ButtonView(View):
    def __init__(self, bot, entry: QueueEntry, paused: bool = False, current_user: Optional[User] = None):
        logging.debug(f"Initializing ButtonView for: {entry.title} with paused state: {paused}")
        print(f"Initializing ButtonView for: {entry.title} with paused state: {paused}")
        super().__init__(timeout=None)
        self.bot = bot
        self.paused = paused
        self.entry = entry
        self.current_user = current_user
        from playback import PlaybackManager
        self.playback_manager = PlaybackManager(queue_manager)
        self.progress_update_task = None  # Track the progress update task

        self.pause_button = Button(label="⏸️ Pause", style=ButtonStyle.primary, custom_id=f"pause-{uuid.uuid4()}")
        self.resume_button = Button(label="▶️ Resume", style=ButtonStyle.primary, custom_id=f"resume-{uuid.uuid4()}")
        self.stop_button = Button(label="⏹️ Stop", style=ButtonStyle.danger, custom_id=f"stop-{uuid.uuid4()}")
        self.skip_button = Button(label="⏭️ Skip", style=ButtonStyle.secondary, custom_id=f"skip-{uuid.uuid4()}")
        self.restart_button = Button(label="🔄 Restart", style=ButtonStyle.secondary, custom_id=f"restart-{uuid.uuid4()}")
        self.shuffle_button = Button(label="🔀 Shuffle", style=ButtonStyle.secondary, custom_id=f"shuffle-{uuid.uuid4()}")
        self.list_queue_button = Button(label="📜 List Queue", style=ButtonStyle.secondary, custom_id=f"list_queue-{uuid.uuid4()}")
        self.remove_button = Button(label="❌ Remove", style=ButtonStyle.danger, custom_id=f"remove-{uuid.uuid4()}")
        self.previous_button = Button(label="⏮️ Previous", style=ButtonStyle.secondary, custom_id=f"previous-{uuid.uuid4()}")
        self.loop_button = Button(label="🔁 Loop", style=ButtonStyle.secondary, custom_id=f"loop-{uuid.uuid4()}")
        self.move_up_button = Button(label="⬆️ Move Up", style=ButtonStyle.secondary, custom_id=f"move_up-{uuid.uuid4()}")
        self.move_down_button = Button(label="⬇️ Move Down", style=ButtonStyle.secondary, custom_id=f"move_down-{uuid.uuid4()}")
        self.move_to_top_button = Button(label="⬆️⬆️ Move to Top", style=ButtonStyle.secondary, custom_id=f"move_to_top-{uuid.uuid4()}")
        self.move_to_bottom_button = Button(label="⬇️⬇️ Move to Bottom", style=ButtonStyle.secondary, custom_id=f"move_to_bottom-{uuid.uuid4()}")

        self.favorite_button = Button(
            label="⭐ Favorite" if not self.is_favorited_by_current_user() else "💛 Favorited",
            style=ButtonStyle.secondary if not self.is_favorited_by_current_user() else ButtonStyle.primary,
            custom_id=f"favorite-{uuid.uuid4()}"
        )

        self.lyrics_button = Button(label="Lyrics", style=ButtonStyle.secondary, custom_id=f"lyrics-{uuid.uuid4()}")

        self.pause_button.callback = self.pause_button_callback
        self.resume_button.callback = self.resume_button_callback
        self.stop_button.callback = self.stop_button_callback
        self.skip_button.callback = self.skip_button_callback
        self.restart_button.callback = self.restart_button_callback
        self.shuffle_button.callback = self.shuffle_button_callback
        self.list_queue_button.callback = self.list_queue_button_callback
        self.remove_button.callback = self.remove_button_callback
        self.previous_button.callback = self.previous_button_callback
        self.loop_button.callback = self.loop_button_callback
        self.move_up_button.callback = self.move_up_button_callback
        self.move_down_button.callback = self.move_down_button_callback
        self.move_to_top_button.callback = self.move_to_top_button_callback
        self.move_to_bottom_button.callback = self.move_to_bottom_button_callback
        self.favorite_button.callback = self.favorite_button_callback
        self.lyrics_button.callback = self.lyrics_button_callback

        self.update_buttons()
        # Start the progress update task when the view is initialized
        asyncio.create_task(self.start_progress_update_task(None, self.entry))

    @staticmethod
    async def send_now_playing_for_buttons(interaction: Interaction, entry: QueueEntry):
        embed = create_now_playing_embed(entry)
        view = ButtonView(interaction.client, entry, paused=False, current_user=interaction.user)
        message = await interaction.channel.send(embed=embed, view=view)
        await schedule_progress_bar_update(interaction, message, entry, ButtonView, queue_manager)

    def is_favorited_by_current_user(self):
        if self.current_user is None:
            return False
        return self.current_user.id in [user['id'] for user in self.entry.favorited_by]

    def update_buttons(self):
        self.clear_items()
        logging.debug(f"Updating buttons with paused state: {self.paused}")
        if self.paused:
            self.add_item(self.resume_button)
        else:
            self.add_item(self.pause_button)

        self.add_item(self.stop_button)
        self.add_item(self.skip_button)
        self.add_item(self.restart_button)
        self.add_item(self.shuffle_button)
        self.add_item(self.list_queue_button)
        self.add_item(self.remove_button)
        self.add_item(self.previous_button)
        self.add_item(self.favorite_button)
        self.add_item(self.lyrics_button)
        logging.debug(f"Checking guild_id attribute for entry: {self.entry.title}")
        print(f"Checking guild_id attribute for entry: {self.entry.title} with guild_id: {self.entry.guild_id}")

        if self.entry.guild_id:
            server_id = str(self.entry.guild_id)
            queue = queue_manager.get_queue(server_id)
            entry_index = queue.index(self.entry) if self.entry in queue else -1
            logging.debug(f"Entry index: {entry_index}, Queue length: {len(queue)}")

            if entry_index > 0:
                logging.debug(f"Adding move up and move to top buttons for {self.entry.title}")
                self.add_item(self.move_up_button)
                self.add_item(self.move_to_top_button)
            if entry_index >= 0 and entry_index < len(queue) - 1:
                logging.debug(f"Adding move down and move to bottom buttons for {self.entry.title}")
                self.add_item(self.move_down_button)
                self.add_item(self.move_to_bottom_button)

        self.loop_button.label = "🔁 Looped" if queue_manager.loop else "🔁 Loop"
        self.loop_button.style = ButtonStyle.primary if queue_manager.loop else ButtonStyle.secondary
        self.add_item(self.loop_button)

    async def refresh_all_views(self):
        for message_id in self.bot.now_playing_messages:
            try:
                channel = self.bot.get_channel(self.entry.guild_id)
                message = await channel.fetch_message(message_id)
                await message.edit(view=self)
            except Exception as e:
                logging.error(f"Error refreshing view for message {message_id}: {e}")

    async def refresh_view(self, interaction: Interaction):
        self.update_buttons()
        await interaction.message.edit(view=self)

    async def lyrics_button_callback(self, interaction: Interaction):
        await handle_lyrics_button(interaction, self.entry)

    async def loop_button_callback(self, interaction: Interaction):
        await handle_loop_button(interaction)

    async def favorite_button_callback(self, interaction: Interaction):
        await handle_favorite_button(interaction, self.entry, self.current_user)

    async def pause_button_callback(self, interaction: Interaction):
        await handle_pause_button(interaction, self.entry, self)

    async def resume_button_callback(self, interaction: Interaction):
        await handle_resume_button(interaction, self.entry, self)

    async def stop_button_callback(self, interaction: Interaction):
        await handle_stop_button(interaction)

    async def skip_button_callback(self, interaction: Interaction):
        await handle_skip_button(interaction)

    async def restart_button_callback(self, interaction: Interaction):
        await handle_restart_button(interaction, self)

    async def shuffle_button_callback(self, interaction: Interaction):
        await handle_shuffle_button(interaction, self)

    async def list_queue_button_callback(self, interaction: Interaction):
        await handle_list_queue_button(interaction, self)

    async def remove_button_callback(self, interaction: Interaction):
        await handle_remove_button(interaction)

    async def previous_button_callback(self, interaction: Interaction):
        await handle_previous_button(interaction)

    async def move_up_button_callback(self, interaction: Interaction):
        await handle_move_up_button(interaction, self.entry)

    async def move_down_button_callback(self, interaction: Interaction):
        await handle_move_down_button(interaction, self.entry)

    async def move_to_top_button_callback(self, interaction: Interaction):
        await handle_move_to_top_button(interaction, self.entry)

    async def move_to_bottom_button_callback(self, interaction: Interaction):
        await handle_move_to_bottom_button(interaction, self.entry)

    async def start_progress_update_task(self, interaction, entry):
        if self.progress_update_task is None:
            logging.debug(f"Starting progress update task with paused state: {queue_manager.is_paused}")
            print(f"Starting progress update task with paused state: {queue_manager.is_paused}")
            self.progress_update_task = asyncio.create_task(schedule_progress_bar_update(
                interaction, interaction.message, entry, ButtonView, queue_manager))
