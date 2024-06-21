import logging
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional
import asyncio

import discord
from discord import ButtonStyle, Embed, File, Interaction
from discord.ui import Button, View
from queue_manager import queue_manager, QueueEntry
from utils import get_lyrics, create_now_playing_embed, schedule_progress_bar_update
# from playback import PlaybackManager

logging.basicConfig(level=logging.DEBUG, filename='views.log', format='%(asctime)s:%(levelname)s:%(message)s')

class ButtonView(View):
    def __init__(self, bot, entry: QueueEntry, paused: bool = False, current_user: Optional[discord.User] = None):
        logging.debug(f"Initializing ButtonView for: {entry.title}")
        super().__init__(timeout=None)
        self.bot = bot
        self.paused = paused
        self.entry = entry
        self.current_user = current_user
        # Avoid circular import by importing PlaybackManager within the method where it's used
        from playback import PlaybackManager
        self.playback_manager = PlaybackManager(queue_manager)

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
                channel = self.bot.get_channel(self.entry.guild_id)  # Assuming the channel ID is the same as the guild ID for simplicity
                message = await channel.fetch_message(message_id)
                await message.edit(view=self)
            except Exception as e:
                logging.error(f"Error refreshing view for message {message_id}: {e}")

    async def refresh_view(self, interaction: Interaction):
        self.update_buttons()
        await interaction.message.edit(view=self)

    async def lyrics_button_callback(self, interaction: Interaction):
        logging.debug(f"Lyrics button clicked for: {self.entry.title}")
        await interaction.response.defer(ephemeral=True)

        lyrics = await get_lyrics(self.entry.title)

        if "Lyrics for " in lyrics:
            lyrics_filename = f"{self.entry.title.replace(' ', '_')}_lyrics.txt"
            with open(lyrics_filename, 'w', encoding='utf-8') as f:
                f.write(lyrics)
            file = File(lyrics_filename, filename=lyrics_filename)
            await interaction.followup.send(file=file)
            os.remove(lyrics_filename)
        else:
            await interaction.followup.send(lyrics)

    async def loop_button_callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        logging.debug("Loop button callback triggered")

        if queue_manager.currently_playing:
            queue_manager.loop = not queue_manager.loop
            self.loop_button.label = "🔁 Looped" if queue_manager.loop else "🔁 Loop"
            self.loop_button.style = ButtonStyle.primary if queue_manager.loop else ButtonStyle.secondary
            await interaction.followup.send(f"Looping {'enabled' if queue_manager.loop else 'disabled'}.")
            logging.info(f"Looping {'enabled' if queue_manager.loop else 'disabled'} for {queue_manager.currently_playing.title}")
            await self.refresh_view(interaction)
        else:
            await interaction.followup.send("No track is currently playing.", ephemeral=True)

    async def favorite_button_callback(self, interaction: Interaction):
        logging.debug("Favorite button callback triggered")
        await interaction.response.defer(ephemeral=True)  # Defer the response to get more time
        user_id = interaction.user.id
        user_name = interaction.user.display_name  # Get the display name (nickname or username)
        if user_id in [user['id'] for user in self.entry.favorited_by]:
            self.entry.favorited_by = [user for user in self.entry.favorited_by if user['id'] != user_id]
            self.entry.is_favorited = False
            self.favorite_button.style = ButtonStyle.secondary
            self.favorite_button.label = "⭐ Favorite"
        else:
            self.entry.favorited_by.append({'id': user_id, 'name': user_name})
            self.entry.is_favorited = True
            self.favorite_button.style = ButtonStyle.primary
            self.favorite_button.label = "💛 Favorited"

        queue_manager.save_queues()
        await self.update_now_playing(interaction)
        await self.refresh_all_views()  # Update all instances of "Now Playing"
        await interaction.followup.send(f"{'Added to' if self.entry.is_favorited else 'Removed from'} favorites.", ephemeral=True)

    async def update_now_playing(self, interaction: Interaction):
        embed = interaction.message.embeds[0]
        favorited_by = ', '.join([user['name'] for user in self.entry.favorited_by]) if self.entry.favorited_by else "No one"
        embed.set_field_at(0, name="Favorited by", value=favorited_by, inline=False)
        await interaction.message.edit(embed=embed, view=self)

    async def pause_button_callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            self.paused = True
            self.update_buttons()
            await interaction.message.edit(view=self)
            await interaction.followup.send('Playback paused.', ephemeral=True)

    async def resume_button_callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            self.paused = False
            self.update_buttons()
            await interaction.message.edit(view=self)
            await interaction.followup.send('Playback resumed.', ephemeral=True)

    async def stop_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        if interaction.guild.voice_client:
            queue_manager.stop_is_triggered = True
            queue_manager.currently_playing = None
            try:
                interaction.guild.voice_client.stop()
            except Exception as e:
                logging.error(f"Error stopping the voice client: {e}")
            await interaction.guild.voice_client.disconnect()
            await interaction.followup.send('Playback stopped and disconnected.', ephemeral=True)

    async def skip_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.followup.send("Queue is empty.", ephemeral=True)
            return

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await interaction.followup.send("Skipped the current track.", ephemeral=True)
        else:
            await interaction.followup.send("Nothing is currently playing.", ephemeral=True)

    async def restart_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        if not queue_manager.currently_playing:
            await interaction.followup.send("No track is currently playing.", ephemeral=True)
            return

        current_entry = queue_manager.currently_playing
        queue_manager.is_restarting = True

        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await self.playback_manager.play_audio(interaction, current_entry)

    async def shuffle_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.followup.send("The queue is currently empty.")
            return
        first_entry_before_shuffle = queue_manager.currently_playing

        queue_manager.has_been_shuffled = True
        random.shuffle(queue)
        for entry in queue:
            entry.has_been_arranged = False
        queue_manager.queues[server_id] = queue
        queue_manager.save_queues()

        titles = [entry.title for entry in queue]
        response = "Queue after shuffle:\n" + "\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

        max_length = 2000  # Discord message character limit
        chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

        for chunk in chunks:
            await interaction.channel.send(chunk)
        
        if first_entry_before_shuffle or any(vc.is_paused() for vc in interaction.guild.voice_clients):
            await self.send_now_playing_for_buttons(interaction, first_entry_before_shuffle)

    async def list_queue_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        server_id = str(interaction.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.followup.send("The queue is currently empty.")
        else:
            titles = [entry.title for entry in queue]
            response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

            max_length = 2000  # Discord message character limit
            chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

            for chunk in chunks:
                await interaction.channel.send(chunk)
            
            if queue_manager.currently_playing:
                await self.send_now_playing_for_buttons(interaction, queue_manager.currently_playing)

    async def remove_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if self.entry in queue:
            queue.remove(self.entry)
            queue_manager.save_queues()
            await interaction.followup.send(f"Removed '{self.entry.title}' from the queue.", ephemeral=True)

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing() and queue_manager.currently_playing == self.entry:
            interaction.guild.voice_client.stop()
            queue_manager.currently_playing = None
            await interaction.followup.send(f"Stopped playback and removed '{self.entry.title}' from the queue.", ephemeral=True)

    async def previous_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response

        server_id = str(interaction.guild.id)
        last_played = queue_manager.last_played_audio.get(server_id)
        if not last_played:
            await interaction.followup.send("There was nothing played prior.", ephemeral=True)
            return

        queue = queue_manager.get_queue(server_id)
        entry = next((e for e in queue if e.title == last_played), None)

        if not entry:
            await interaction.followup.send("No previously played track found.", ephemeral=True)
            return

        queue.remove(entry)
        queue.insert(1, entry)
        queue_manager.save_queues()
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await self.playback_manager.play_audio(interaction, entry)
            await self.refresh_view(interaction)

    async def move_up_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        entry_index = queue.index(self.entry)
        
        if entry_index > 0:
            queue.insert(entry_index - 1, queue.pop(entry_index))
            self.entry.has_been_arranged = True
            queue_manager.save_queues()
            await interaction.followup.send(f"Moved '{self.entry.title}' up in the queue.", ephemeral=True)
            await self.refresh_view(interaction)
        else:
            await interaction.followup.send(f"'{self.entry.title}' is already at the top of the queue.", ephemeral=True)

    async def move_down_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        entry_index = queue.index(self.entry)
        
        if entry_index < len(queue) - 1:
            queue.insert(entry_index + 1, queue.pop(entry_index))
            self.entry.has_been_arranged = True
            queue_manager.save_queues()
            await interaction.followup.send(f"Moved '{self.entry.title}' down in the queue.", ephemeral=True)
            await self.refresh_view(interaction)
        else:
            await interaction.followup.send(f"'{self.entry.title}' is already at the bottom of the queue.", ephemeral=True)

    async def move_to_top_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        entry_index = queue.index(self.entry)
        
        if entry_index > 0:
            queue.insert(0, queue.pop(entry_index))
            self.entry.has_been_arranged = True
            queue_manager.save_queues()
            await interaction.followup.send(f"Moved '{self.entry.title}' to the top of the queue.", ephemeral=True)
            await self.refresh_view(interaction)
        else:
            await interaction.followup.send(f"'{self.entry.title}' is already at the top of the queue.", ephemeral=True)

    async def move_to_bottom_button_callback(self, interaction: Interaction):
        await interaction.response.defer()  # Defer the response
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        entry_index = queue.index(self.entry)
        
        if entry_index < len(queue) - 1:
            queue.append(queue.pop(entry_index))
            self.entry.has_been_arranged = True
            queue_manager.save_queues()
            await interaction.followup.send(f"Moved '{self.entry.title}' to the bottom of the queue.", ephemeral=True)
            await self.refresh_view(interaction)
        else:
            await interaction.followup.send(f"'{self.entry.title}' is already at the bottom of the queue.", ephemeral=True)
