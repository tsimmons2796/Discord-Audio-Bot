import json
import uuid
from datetime import datetime, timedelta
import logging
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
import asyncio
from concurrent.futures import ThreadPoolExecutor
import random
import aiohttp
import re
from typing import List, Dict, Optional
from discord import Attachment

logging.basicConfig(level=logging.DEBUG, filename='queue_log.log', format='%(asctime)s:%(levelname)s:%(message)s')

class QueueEntry:
    def __init__(self, video_url: str, best_audio_url: str, title: str, is_playlist: bool, thumbnail: str = '', playlist_index: Optional[int] = None, duration: int = 0, is_favorited: bool = False, favorited_by: Optional[List[Dict[str, str]]] = None, has_been_arranged: bool = False, timestamp: Optional[str] = None):
        logging.debug(f"Creating QueueEntry: {title}, URL: {video_url}")
        self.video_url = video_url
        self.best_audio_url = best_audio_url
        self.title = title
        self.is_playlist = is_playlist
        self.playlist_index = playlist_index
        self.thumbnail = thumbnail
        self.duration = duration
        self.is_favorited = is_favorited
        self.favorited_by = favorited_by if favorited_by is not None else []
        self.has_been_arranged = has_been_arranged
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self):
        return {
            'video_url': self.video_url,
            'best_audio_url': self.best_audio_url,
            'title': self.title,
            'is_playlist': self.is_playlist,
            'playlist_index': self.playlist_index,
            'thumbnail': self.thumbnail,
            'is_favorited': self.is_favorited,
            'favorited_by': self.favorited_by,
            'has_been_arranged': self.has_been_arranged,
            'timestamp': self.timestamp
        }

    async def refresh_url(self):
        logging.debug(f"Refreshing URL for: {self.title}")
        if 'youtube.com' in self.video_url or 'youtu.be' in self.video_url:
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'ignoreerrors': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_running_loop().run_in_executor(None, lambda: ydl.extract_info(self.video_url, download=False))
                if info:
                    self.best_audio_url = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), self.video_url)
                    self.timestamp = datetime.now().isoformat()  # Update the timestamp after refreshing
                    logging.info(f"URL refreshed for {self.title}. New URL: {self.best_audio_url}")

class BotQueue:
    def __init__(self):
        logging.debug("Initializing BotQueue")
        self.currently_playing = None
        self.queues = self.load_queues()
        self.ensure_today_queue_exists()
        self.last_played_audio = self.load_last_played_audio()
        self.is_restarting = False
        self.has_been_shuffled = False
        self.stop_is_triggered = False
        self.loop = False

    def load_queues(self) -> Dict[str, List[QueueEntry]]:
        logging.debug("Loading queues from file")
        try:
            with open('queues.json', 'r') as file:
                queues_data = json.load(file)
            return {date: [QueueEntry(**entry) for entry in entries] for date, entries in queues_data.items()}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Failed to load queues: {e}")
            return {}

    def load_last_played_audio(self) -> Optional[str]:
        logging.debug("Loading last played audio from file")
        try:
            with open('last_played_audio.json', 'r') as file:
                return json.load(file).get('last_played_audio')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load last played audio: {e}")
            return None

    def save_queues(self):
        logging.debug("Saving queues to file")
        try:
            with open('queues.json', 'w') as file:
                json.dump({k: [entry.to_dict() for entry in v] for k, v in self.queues.items()}, file, indent=4)
            with open('last_played_audio.json', 'w') as file:
                if self.last_played_audio is None:
                    json.dump({'last_played_audio': None}, file, indent=4)
                else:
                    json.dump({'last_played_audio': self.last_played_audio}, file, indent=4)
        except Exception as e:
            logging.error(f"Failed to save queues or last played audio: {e}")

    def get_queue(self, date_str: str) -> List[QueueEntry]:
        logging.debug(f"Getting queue for date: {date_str}")
        return self.queues.get(date_str, [])

    def add_to_queue(self, entry: QueueEntry):
        date_str = datetime.now().strftime('%Y-%m-%d')
        if date_str not in self.queues:
            self.queues[date_str] = []
        self.queues[date_str].append(entry)
        self.save_queues()
        logging.info(f"Added {entry.title} to queue on {date_str}")

    def ensure_today_queue_exists(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        if today_str not in self.queues:
            self.queues[today_str] = []
            self.save_queues()
            logging.info(f"Created a new queue for today: {today_str}")

queue_manager = BotQueue()
executor = ThreadPoolExecutor(max_workers=1)

async def fetch_info(url, index: int = None):
    logging.debug(f"Fetching info for URL: {url}, Index: {index}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': False if "list=" in url else True,
        'playlist_items': str(index) if index is not None else None,
        'ignoreerrors': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
        if 'duration' not in info and 'entries' in info:
            info['duration'] = sum(entry['duration'] for entry in info['entries'] if 'duration' in entry)
        logging.info(f"Fetched info: {info}")
        return info

async def fetch_playlist_length(url):
    logging.debug(f"Fetching playlist length for URL: {url}")
    ydl_opts = {'quiet': True, 'noplaylist': False, 'extract_entries': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
        length = len(info.get('entries', []))
        logging.info(f"Playlist length: {length}")
        return length

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename)

async def download_file(url: str, dest_folder: str) -> str:
    logging.debug(f"Downloading file from URL: {url}")
    os.makedirs(dest_folder, exist_ok=True)
    filename = sanitize_filename(os.path.basename(url))
    file_path = os.path.join(dest_folder, filename)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    f.write(await response.read())
                logging.info(f"Downloaded file: {file_path}")
                return file_path
            else:
                logging.error(f"Failed to download file: {url}")
                return None

async def play_audio(ctx_or_interaction, entry):
    logging.debug(f"Preparing to play audio for: {entry.title}")
    entry_timestamp = datetime.fromisoformat(entry.timestamp)
    if datetime.now() - entry_timestamp > timedelta(hours=3):
        await entry.refresh_url()

    queue_manager.currently_playing = entry
    queue_manager.save_queues()

    logging.info(f"Starting playback for: {entry.title} (URL: {entry.best_audio_url})")

    def after_playing(error):
        queue_manager.stop_is_triggered = False
        if error:
            logging.error(f"Error playing {entry.title}: {error}")
            bot_client = ctx_or_interaction.client if hasattr(ctx_or_interaction, 'client') else ctx_or_interaction.bot
            asyncio.run_coroutine_threadsafe(ctx_or_interaction.channel.send("Error occurred during playback."), bot_client.loop).result()
        else:
            logging.info(f"Finished playing {entry.title} at {datetime.now()}")

            if not queue_manager.is_restarting and not queue_manager.has_been_shuffled and not entry.has_been_arranged:
                date_str = datetime.now().strftime('%Y-%m-%d')
                queue = queue_manager.get_queue(date_str)
                if entry in queue:
                    queue.remove(entry)
                    queue.append(entry)
                    queue_manager.save_queues()
                    logging.info(f"Moved {entry.title} to the bottom of the queue")

            if queue_manager.loop:
                logging.info(f"Looping {entry.title}")
                bot_client = ctx_or_interaction.client if hasattr(ctx_or_interaction, 'client') else ctx_or_interaction.bot
                asyncio.run_coroutine_threadsafe(play_audio(ctx_or_interaction, entry), bot_client.loop).result()
            else:
                if not queue_manager.is_restarting:
                    queue_manager.last_played_audio = entry.title
                queue_manager.save_queues()
                bot_client = ctx_or_interaction.client if hasattr(ctx_or_interaction, 'client') else ctx_or_interaction.bot
                asyncio.run_coroutine_threadsafe(play_next(ctx_or_interaction), bot_client.loop).result()

    async def start_playback():
        try:
            logging.debug("Starting playback")
            voice_client = ctx_or_interaction.guild.voice_client
            audio_source = discord.FFmpegPCMAudio(
                entry.best_audio_url,
                options='-bufsize 65536k -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -vn'
            )
            if not voice_client.is_playing():
                voice_client.play(audio_source, after=after_playing)
                await send_now_playing(ctx_or_interaction, entry)
                queue_manager.has_been_shuffled = False
                logging.info(f"Playback started for {entry.title} at {datetime.now()}")
        except Exception as e:
            if not queue_manager.stop_is_triggered:
                logging.error(f"Exception during playback: {e}")
                await ctx_or_interaction.channel.send(f"An error occurred during playback: {e}")

    await start_playback()

async def send_now_playing(interaction, entry, paused=False):
    logging.debug(f"Sending now playing message for: {entry.title}")
    embed = discord.Embed(title="Now Playing", description=entry.title, url=entry.video_url)
    embed.set_thumbnail(url=entry.thumbnail)
    embed.add_field(name="URL", value=entry.video_url, inline=False)
    embed.add_field(name="Favorited by", value=', '.join([user['name'] for user in entry.favorited_by]), inline=False)

    view = ButtonView(interaction.client, entry, paused=paused)
    message = await interaction.channel.send(embed=embed, view=view)
    await update_progress_bar(interaction, message, entry)

async def update_progress_bar(interaction, message, entry):
    logging.debug(f"Updating progress bar for: {entry.title}")
    duration = entry.duration if hasattr(entry, 'duration') else 300
    start_time = datetime.now()
    while True:
        elapsed = (datetime.now() - start_time).seconds
        if elapsed >= duration:
            break
        progress = elapsed / duration
        progress_bar = "[" + "=" * int(progress * 20) + " " * (20 - int(progress * 20)) + "]"
        embed = message.embeds[0]
        embed.set_field_at(0, name="Progress", value=progress_bar, inline=False)
        await message.edit(embed=embed)
        await asyncio.sleep(10)

async def play_next(interaction):
    logging.debug("Playing next track in the queue")
    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    if queue and queue_manager.currently_playing:
        current_entry = queue_manager.currently_playing
        if current_entry in queue and not queue_manager.is_restarting:
            if not current_entry.has_been_arranged and not queue_manager.has_been_shuffled:
                queue.remove(current_entry)
                queue.append(current_entry)
            queue_manager.save_queues()

        queue_manager.is_restarting = False

        if queue:
            entry = queue[0]
            await play_audio(interaction, entry)

async def process_play_command(interaction, url):
    logging.debug(f"Processing play command for URL: {url}")
    first_video_info = await fetch_info(url, index=1)
    if not first_video_info or 'entries' not in first_video_info or not first_video_info['entries']:
        await interaction.response.send_message("Could not retrieve the first video of the playlist.")
        return

    first_video = first_video_info['entries'][0]
    if first_video:
        first_entry = QueueEntry(
            video_url=first_video.get('webpage_url', ''),
            best_audio_url=next((f['url'] for f in first_video['formats'] if f.get('acodec') != 'none'), ''),
            title=first_video.get('title', 'Unknown title'),
            is_playlist=True,
            thumbnail=first_video.get('thumbnail', ''),
            playlist_index=1,
            duration=first_video.get('duration', 0)
        )
        queue_manager.add_to_queue(first_entry)
        await interaction.response.send_message(f"Added to queue: {first_entry.title}")
        await play_audio(interaction, first_entry)
    else:
        await interaction.response.send_message("No video found at the specified index.")
        return

    playlist_length = await fetch_playlist_length(url)
    if playlist_length > 1:
        for index in range(2, playlist_length + 1):
            try:
                info = await fetch_info(url, index=index)
                if info and 'entries' in info and info['entries']:
                    video = info['entries'][0]
                    entry = QueueEntry(
                        video_url=video.get('webpage_url', ''),
                        best_audio_url=next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), ''),
                        title=video.get('title', 'Unknown title'),
                        is_playlist=True,
                        thumbnail=video.get('thumbnail', ''),
                        playlist_index=index,
                        duration=video.get('duration', 0)
                    )
                    queue_manager.add_to_queue(entry)
                    await interaction.channel.send(f"Added to queue: {entry.title}")
            except yt_dlp.utils.ExtractorError as e:
                logging.warning(f"Skipping unavailable video at index {index}: {str(e)}")
                await interaction.channel.send(f"Skipping unavailable video at index {index}")

    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    titles = [entry.title for entry in queue]
    response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
    await interaction.response.send_message(response)

async def process_single_video_or_mp3(url, interaction):
    logging.debug(f"Processing single video or MP3 for URL: {url}")
    if url.lower().endswith('.mp3'):
        return QueueEntry(video_url=url, best_audio_url=url, title=url.split('/')[-1], is_playlist=False)
    else:
        video_info = await fetch_info(url)
        if video_info:
            return QueueEntry(
                video_url=video_info.get('webpage_url', url),
                best_audio_url=next((f['url'] for f in video_info['formats'] if f.get('acodec') != 'none'), url),
                title=video_info.get('title', 'Unknown title'),
                is_playlist=False,
                thumbnail=video_info.get('thumbnail', '')
            )
        else:
            await interaction.response.send_message("Error retrieving video data.")
            return None

async def handle_playlist(interaction, entries):
    logging.debug("Handling playlist")
    for index, video in enumerate(entries, start=1):
        entry = QueueEntry(
            video_url=video.get('webpage_url', ''),
            best_audio_url=next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), ''),
            title=video.get('title', 'Unknown title'),
            is_playlist=True,
            thumbnail=video.get('thumbnail', ''),
            playlist_index=index
        )
        queue_manager.add_to_queue(entry)
        if index == 1:
            await play_audio(interaction, entry)

async def handle_single_video(interaction, info):
    logging.debug(f"Handling single video: {info['title']}")
    entry = QueueEntry(
        video_url=info.get('webpage_url', ''),
        best_audio_url=next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), ''),
        title=info.get('title', 'Unknown title'),
        is_playlist=False,
        thumbnail=info.get('thumbnail', '')
    )
    queue_manager.add_to_queue(entry)
    await play_audio(interaction, entry)

class AudioBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        logging.debug("Initializing AudioBot")
        super().__init__(command_prefix, intents=intents)

    async def setup_hook(self):
        logging.debug("Setting up hook for AudioBot")
        dummy_entry = QueueEntry(video_url='', best_audio_url='', title='dummy', is_playlist=False)
        self.add_view(ButtonView(self, dummy_entry))
        await self.tree.sync()

    async def on_ready(self):
        logging.info(f'{self.user} is now connected and ready.')
        print(f'{self.user} is now connected and ready.')

class ButtonView(discord.ui.View):
    def __init__(self, bot, entry: QueueEntry, paused: bool = False):
        logging.debug(f"Initializing ButtonView for: {entry.title}")
        super().__init__(timeout=None)
        self.bot = bot
        self.paused = paused
        self.entry = entry

        self.pause_button_id = f"pause-{uuid.uuid4()}"
        self.resume_button_id = f"resume-{uuid.uuid4()}"
        self.stop_button_id = f"stop-{uuid.uuid4()}"
        self.skip_button_id = f"skip-{uuid.uuid4()}"
        self.restart_button_id = f"restart-{uuid.uuid4()}"
        self.shuffle_button_id = f"shuffle-{uuid.uuid4()}"
        self.list_queue_button_id = f"list_queue-{uuid.uuid4()}"
        self.remove_button_id = f"remove-{uuid.uuid4()}"
        self.previous_button_id = f"previous-{uuid.uuid4()}"
        self.favorite_button_id = f"favorite-{uuid.uuid4()}"
        self.loop_button_id = f"loop-{uuid.uuid4()}"
        self.move_up_button_id = f"move_up-{uuid.uuid4()}"
        self.move_down_button_id = f"move_down-{uuid.uuid4()}"
        self.move_to_top_button_id = f"move_to_top-{uuid.uuid4()}"
        self.move_to_bottom_button_id = f"move_to_bottom-{uuid.uuid4()}"

        self.pause_button = discord.ui.Button(label="⏸️ Pause", style=discord.ButtonStyle.primary, custom_id=self.pause_button_id)
        self.resume_button = discord.ui.Button(label="▶️ Resume", style=discord.ButtonStyle.primary, custom_id=self.resume_button_id)
        self.stop_button = discord.ui.Button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id=self.stop_button_id)
        self.skip_button = discord.ui.Button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id=self.skip_button_id)
        self.restart_button = discord.ui.Button(label="🔄 Restart", style=discord.ButtonStyle.secondary, custom_id=self.restart_button_id)
        self.shuffle_button = discord.ui.Button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, custom_id=self.shuffle_button_id)
        self.list_queue_button = discord.ui.Button(label="📜 List Queue", style=discord.ButtonStyle.secondary, custom_id=self.list_queue_button_id)
        self.remove_button = discord.ui.Button(label="❌ Remove", style=discord.ButtonStyle.danger, custom_id=self.remove_button_id)
        self.previous_button = discord.ui.Button(label="⏮️ Previous", style=discord.ButtonStyle.secondary, custom_id=self.previous_button_id)
        self.loop_button = discord.ui.Button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id=self.loop_button_id)
        self.move_up_button = discord.ui.Button(label="⬆️ Move Up", style=discord.ButtonStyle.secondary, custom_id=self.move_up_button_id)
        self.move_down_button = discord.ui.Button(label="⬇️ Move Down", style=discord.ButtonStyle.secondary, custom_id=self.move_down_button_id)
        self.move_to_top_button = discord.ui.Button(label="⬆️⬆️ Move to Top", style=discord.ButtonStyle.secondary, custom_id=self.move_to_top_button_id)
        self.move_to_bottom_button = discord.ui.Button(label="⬇️⬇️ Move to Bottom", style=discord.ButtonStyle.secondary, custom_id=self.move_to_bottom_button_id)

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

        self.favorite_button = discord.ui.Button(
            label="⭐ Favorite" if not self.entry.is_favorited else "💛 Favorited",
            style=discord.ButtonStyle.secondary if not self.entry.is_favorited else discord.ButtonStyle.primary,
            custom_id=self.favorite_button_id
        )
        self.favorite_button.callback = self.favorite_button_callback

        self.update_buttons()

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

        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        entry_index = queue.index(self.entry) if self.entry in queue else -1

        if entry_index > 0:
            self.add_item(self.move_up_button)
            self.add_item(self.move_to_top_button)
        if entry_index >= 0 and entry_index < len(queue) - 1:
            self.add_item(self.move_down_button)
            self.add_item(self.move_to_bottom_button)

        self.loop_button.label = "🔁 Looped" if queue_manager.loop else "🔁 Loop"
        self.add_item(self.loop_button)

    async def refresh_view(self, interaction):
        self.update_buttons()
        await interaction.message.edit(view=self)

    async def loop_button_callback(self, interaction: discord.Interaction):
        logging.debug("Loop button callback triggered")
        if queue_manager.currently_playing:
            queue_manager.loop = not queue_manager.loop
            self.loop_button.label = "🔁 Looped" if queue_manager.loop else "🔁 Loop"
            await interaction.response.send_message(f"Looping {'enabled' if queue_manager.loop else 'disabled'}.")
            logging.info(f"Looping {'enabled' if queue_manager.loop else 'disabled'} for {queue_manager.currently_playing.title}")
            await self.refresh_view(interaction)
        else:
            await interaction.response.send_message("No track is currently playing.", ephemeral=True)

    async def favorite_button_callback(self, interaction: discord.Interaction):
        logging.debug("Favorite button callback triggered")
        await interaction.response.defer()  # Defer the response to get more time
        user_id = interaction.user.id
        user_name = interaction.user.display_name  # Get the display name (nickname or username)
        if user_id in [user['id'] for user in self.entry.favorited_by]:
            self.entry.favorited_by = [user for user in self.entry.favorited_by if user['id'] != user_id]
            self.entry.is_favorited = False
            self.favorite_button.style = discord.ButtonStyle.secondary
            self.favorite_button.label = "⭐ Favorite"
        else:
            self.entry.favorited_by.append({'id': user_id, 'name': user_name})
            self.entry.is_favorited = True
            self.favorite_button.style = discord.ButtonStyle.primary
            self.favorite_button.label = "💛 Favorited"

        queue_manager.save_queues()
        await self.update_now_playing(interaction)
        await interaction.followup.send(f"{'Added to' if self.entry.is_favorited else 'Removed from'} favorites.", ephemeral=True)

    async def update_now_playing(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        embed.set_field_at(1, name="Favorited by", value=', '.join([user['name'] for user in self.entry.favorited_by]), inline=False)
        await interaction.message.edit(embed=embed, view=self)

    async def pause_button_callback(self, interaction: discord.Interaction):
        logging.debug("Pause button callback triggered")
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            self.paused = True
            await self.refresh_view(interaction)
            await interaction.response.send_message('Playback paused.', ephemeral=True)

    async def resume_button_callback(self, interaction: discord.Interaction):
        logging.debug("Resume button callback triggered")
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            self.paused = False
            await self.refresh_view(interaction)
            await interaction.response.send_message('Playback resumed.', ephemeral=True)

    async def stop_button_callback(self, interaction: discord.Interaction):
        logging.debug("Stop button callback triggered")
        if interaction.guild.voice_client:
            queue_manager.stop_is_triggered = True
            interaction.guild.voice_client.stop()
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message('Playback stopped and disconnected.', ephemeral=True)

    async def skip_button_callback(self, interaction: discord.Interaction):
        logging.debug("Skip button callback triggered")
        date_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(date_str)
        if not queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            # await play_next(interaction)
            await interaction.response.send_message("Skipped the current track.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)

    async def restart_button_callback(self, interaction: discord.Interaction):
        logging.debug("Restart button callback triggered")
        await interaction.response.defer()  # Defer the response
        if not queue_manager.currently_playing:
            await interaction.response.send_message("No track is currently playing.", ephemeral=True)
            return

        current_entry = queue_manager.currently_playing
        queue_manager.is_restarting = True

        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await play_audio(interaction, current_entry)

    async def shuffle_button_callback(self, interaction: discord.Interaction):
        logging.debug("Shuffle button callback triggered")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return
        first_entry_before_shuffle = queue_manager.currently_playing

        queue_manager.has_been_shuffled = True
        random.shuffle(queue)
        for entry in queue:
            entry.has_been_arranged = False
        queue_manager.queues[today_str] = queue
        queue_manager.save_queues()

        titles = [entry.title for entry in queue]
        response = "Queue after shuffle:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
        await interaction.response.send_message(response)
        await send_now_playing(interaction, first_entry_before_shuffle)

    async def list_queue_button_callback(self, interaction: discord.Interaction):
        logging.debug("List queue button callback triggered")
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
        else:
            titles = [entry.title for entry in queue]
            response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

            max_length = 2000
            chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

            for chunk in chunks:
                await interaction.response.send_message(chunk)
            await send_now_playing(interaction, queue_manager.currently_playing)

    async def remove_button_callback(self, interaction: discord.Interaction):
        logging.debug("Remove button callback triggered")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if self.entry in queue:
            queue.remove(self.entry)
            queue_manager.save_queues()
            await interaction.response.send_message(f"Removed '{self.entry.title}' from the queue.", ephemeral=True)

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing() and queue_manager.currently_playing == self.entry:
            interaction.guild.voice_client.stop()
            queue_manager.currently_playing = None
            await interaction.response.send_message(f"Stopped playback and removed '{self.entry.title}' from the queue.", ephemeral=True)

    async def previous_button_callback(self, interaction: discord.Interaction):
        logging.debug("Previous button callback triggered")
        await interaction.response.defer()

        last_played = queue_manager.last_played_audio
        if not last_played:
            await interaction.followup.send("There was nothing played prior.", ephemeral=True)
            return

        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
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
            await play_audio(interaction, entry)
            await self.refresh_view(interaction)

    async def move_up_button_callback(self, interaction: discord.Interaction):
        logging.debug("Move up button callback triggered")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        entry_index = queue.index(self.entry)
        
        if entry_index > 0:
            queue.insert(entry_index - 1, queue.pop(entry_index))
            self.entry.has_been_arranged = True
            queue_manager.save_queues()
            await interaction.response.send_message(f"Moved '{self.entry.title}' up in the queue.", ephemeral=True)
            await self.refresh_view(interaction)
        else:
            await interaction.response.send_message(f"'{self.entry.title}' is already at the top of the queue.", ephemeral=True)

    async def move_down_button_callback(self, interaction: discord.Interaction):
        logging.debug("Move down button callback triggered")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        entry_index = queue.index(self.entry)
        
        if entry_index < len(queue) - 1:
            queue.insert(entry_index + 1, queue.pop(entry_index))
            self.entry.has_been_arranged = True
            queue_manager.save_queues()
            await interaction.response.send_message(f"Moved '{self.entry.title}' down in the queue.", ephemeral=True)
            await self.refresh_view(interaction)
        else:
            await interaction.response.send_message(f"'{self.entry.title}' is already at the bottom of the queue.", ephemeral=True)

    async def move_to_top_button_callback(self, interaction: discord.Interaction):
        logging.debug("Move to top button callback triggered")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        entry_index = queue.index(self.entry)
        
        if entry_index > 0:
            queue.insert(0, queue.pop(entry_index))
            self.entry.has_been_arranged = True
            queue_manager.save_queues()
            await interaction.response.send_message(f"Moved '{self.entry.title}' to the top of the queue.", ephemeral=True)
            await self.refresh_view(interaction)
        else:
            await interaction.response.send_message(f"'{self.entry.title}' is already at the top of the queue.", ephemeral=True)

    async def move_to_bottom_button_callback(self, interaction: discord.Interaction):
        logging.debug("Move to bottom button callback triggered")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        entry_index = queue.index(self.entry)
        
        if entry_index < len(queue) - 1:
            queue.append(queue.pop(entry_index))
            self.entry.has_been_arranged = True
            queue_manager.save_queues()
            await interaction.response.send_message(f"Moved '{self.entry.title}' to the bottom of the queue.", ephemeral=True)
            await self.refresh_view(interaction)

async def send_now_playing(interaction, entry, paused=False):
    logging.debug(f"Sending now playing message for: {entry.title}")
    embed = discord.Embed(title="Now Playing", description=entry.title, url=entry.video_url)
    embed.set_thumbnail(url=entry.thumbnail)
    embed.add_field(name="URL", value=entry.video_url, inline=False)
    embed.add_field(name="Favorited by", value=', '.join([user['name'] for user in entry.favorited_by]), inline=False)

    view = ButtonView(interaction.client, entry, paused=paused)
    message = await interaction.channel.send(embed=embed, view=view)
    await update_progress_bar(interaction, message, entry)

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.debug("Initializing MusicCommands Cog")
        
    @app_commands.command(name='loop', description='Toggle looping of the current track.')
    async def loop(self, interaction: discord.Interaction):
        logging.debug("Loop command executed")
        if queue_manager.currently_playing:
            queue_manager.loop = not queue_manager.loop
            await interaction.response.send_message(f"Looping {'enabled' if queue_manager.loop else 'disabled'}.")
            logging.info(f"Looping {'enabled' if queue_manager.loop else 'disabled'} for {queue_manager.currently_playing.title}")
        else:
            await interaction.response.send_message("No track is currently playing.")

    @app_commands.command(name='play', description='Play a URL or attached MP3 file.')
    async def play(self, interaction: discord.Interaction, url: str = None, mp3_file: Optional[Attachment] = None):
        voice_client = interaction.guild.voice_client
        if not voice_client and interaction.user.voice:
            voice_client = await interaction.user.voice.channel.connect()
        elif not voice_client:
            await interaction.response.send_message("You are not connected to a voice channel.")
            return

        await interaction.response.defer()

        if mp3_file:
            file_path = await download_file(mp3_file.url, 'Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s')
            if file_path:
                entry = QueueEntry(
                    video_url=mp3_file.url,
                    best_audio_url=file_path,
                    title=mp3_file.filename,
                    is_playlist=False,
                    playlist_index=None
                )
                queue_manager.add_to_queue(entry)
                if not voice_client.is_playing():
                    await play_audio(interaction, entry)
            await interaction.followup.send(f"Added {entry.title} to the queue.")
            return

        if url:
            if "list=" in url:
                playlist_length = await fetch_playlist_length(url)
                for index in range(1, playlist_length + 1):
                    video_info = await fetch_info(url, index=index)
                    if video_info and 'entries' in video_info:
                        video = video_info['entries'][0] if video_info['entries'] else None
                        if video:
                            entry = QueueEntry(
                                video_url=video['webpage_url'],
                                best_audio_url=next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), ''),
                                title=video['title'],
                                is_playlist=True,
                                playlist_index=index
                            )
                            queue_manager.add_to_queue(entry)
                            await interaction.channel.send(f"Added to queue: {entry.title}")
                            if index == 1 or not voice_client.is_playing():
                                await play_audio(interaction, entry)
                    else:
                        await interaction.followup.send(f"Failed to retrieve video at index {index}")
                        break
            else:
                entry = await process_single_video_or_mp3(url, interaction)
                if entry:
                    queue_manager.add_to_queue(entry)
                    if not voice_client.is_playing():
                        await play_audio(interaction, entry)
            await interaction.followup.send(f"Added '{entry.title}' to the queue.")
            return
        else:
            await interaction.followup.send("Please provide a valid URL or attach an MP3 file.")

    @app_commands.command(name='previous', description='Play the last entry that was being played.')
    async def previous(self, interaction: discord.Interaction):
        logging.debug("Previous command executed")
        last_played = queue_manager.last_played_audio
        if not last_played:
            await interaction.response.send_message("There was nothing played prior.")
            return

        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        entry = next((e for e in queue if e.title == last_played), None)

        if not entry:
            await interaction.response.send_message("No previously played track found.")
            return

        queue.remove(entry)
        queue.insert(1, entry)
        queue_manager.save_queues()
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await send_now_playing(interaction, entry, paused=False)

    @app_commands.command(name='help', description='Show the help text.')
    async def help_command(self, interaction: discord.Interaction):
        logging.debug("Help command executed")
        help_text = """
        Here are the commands and buttons you can use:

        **Commands:**

        **/play [URL or attachment]**
        - Plays audio from a YouTube URL or an attached MP3 file.
        - If a URL is provided, it can be a single video or a playlist. If it's a playlist, all videos will be added to the queue.
        - If an MP3 file is attached, it will be added to the queue and played if nothing is currently playing.

        **.mp3_list [URL or attachment]**
        - Similar to /play but works specifically for attached MP3 files including more than one mp3 file.
        - Multiple MP3 files can be attached, and all will be added to the queue.

        **/play_video [title]**
        - Plays a specific video from the queue by its title.
        - If a title is provided and found in the queue, it will start playing immediately.

        **/shuffle**
        - Randomly shuffles the current queue and shows the new order.

        **/list_queue**
        - Lists all entries currently in the queue.
        - Displays the current queue with each track's title and position.

        **/play_queue**
        - Starts playing the queue from the first track.

        **/remove_by_title [title]**
        - Removes a specific track by its title from the queue.
        - If the title is found in the queue, it will be removed.

        **/skip**
        - Skips the current track and plays the next one in the queue.
        - If there is no next track, the playback stops.

        **/pause**
        - Pauses the currently playing track.

        **/resume**
        - Resumes playback if it is paused.

        **/stop**
        - Stops playback and disconnects the bot from the voice channel.

        **/restart**
        - Restarts the currently playing track from the beginning.

        **/remove_queue [index]**
        - Removes a track from the queue by its index.
        - The index is the position in the queue, starting from 1.

        **Buttons:**

        **⏸️ Pause**
        - Pauses the currently playing track.

        **▶️ Resume**
        - Resumes playback if it is paused.

        **⏹️ Stop**
        - Stops playback and disconnects the bot from the voice channel.

        **⏭️ Skip**
        - Skips the current track and plays the next one in the queue.

        **🔄 Restart**
        - Restarts the currently playing track from the beginning.

        **🔀 Shuffle**
        - Randomly shuffles the current queue and shows the new order.

        **📜 List Queue**
        - Lists all entries currently in the queue.
        - Displays the current queue with each track's title and position.

        **❌ Remove**
        - Removes the current track from the queue.
        - If the removed track is currently playing, playback stops.

        **⏮️ /previous**
        - Plays the last entry that was being played.
        - Useful for returning to the previously played track.

        **🔁 Loop**
        - Toggles looping of the current track.
        - If enabled, the current track will repeat after it finishes playing.
        - Continues looping the current track until loop button is clicked again.

        **⬆️ Move Up**
        - Moves the current track up one position in the queue.

        **⬇️ Move Down**
        - Moves the current track down one position in the queue.

        **⬆️⬆️ Move to Top**
        - Moves the current track to the top of the queue.

        **⬇️⬇️ Move to Bottom**
        - Moves the current track to the bottom of the queue.

        **⭐ Favorite / 💛 Favorited**
        - Toggles the favorite status of the current track.
        - Users can mark tracks as favorites, which will be displayed in the "Now Playing" embed.

        Type a command to execute it. For example: `/play https://youtube.com/watch?v=example`

        **Always taking suggestions for the live service of Radio-Bot**
        """
        max_length = 2000
        chunks = [help_text[i:i+max_length] for i in range(0, len(help_text), max_length)]

        for chunk in chunks:
            await interaction.response.send_message(chunk)

    @app_commands.command(name='play_video', description='Play a video from the queue by title.')
    async def play_video(self, interaction: discord.Interaction, title: str):
        logging.debug(f"Play video command executed for title: {title}")
        await interaction.response.defer()  # Defer the interaction response

        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)

        entry_index = next((i for i, entry in enumerate(queue) if entry.title == title), None)
        if entry_index is None:
            await interaction.followup.send(f"No video found with title '{title}'.")
            return

        entry = queue.pop(entry_index)

        if interaction.guild.voice_client:
            if interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused():
                if 'Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s' in entry.best_audio_url:
                    logging.info(f'Moving {entry.title} to the front of the queue.')
                    queue.insert(0, entry)
                    interaction.guild.voice_client.stop()
                else:
                    logging.info(f'Moving {entry.title} to second in position.')
                    queue.insert(1, entry)
                    interaction.guild.voice_client.stop()
                await asyncio.sleep(1)

        if not interaction.guild.voice_client:
            if interaction.user.voice:
                queue.insert(0, entry)
                await interaction.user.voice.channel.connect()
                await play_audio(interaction, entry)
            else:
                await interaction.followup.send("You are not connected to a voice channel.")
                return

        await interaction.followup.send(f"Playing video: {title}")

    @app_commands.command(name='remove_by_title', description='Remove a track from the queue by title.')
    async def remove_by_title(self, interaction: discord.Interaction, title: str):
        logging.debug(f"Remove by title command executed for title: {title}")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return

        original_length = len(queue)
        queue = [entry for entry in queue if entry.title != title]
        if len(queue) == original_length:
            await interaction.response.send_message(f"No track found with title '{title}'.")
        else:
            queue_manager.queues[today_str] = queue
            queue_manager.save_queues()
            await interaction.response.send_message(f"Removed '{title}' from the queue.")

    @app_commands.command(name='shuffle', description='Shuffle the current queue.')
    async def shuffle(self, interaction: discord.Interaction):
        logging.debug("Shuffle command executed")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return
        first_entry_before_shuffle = queue_manager.currently_playing

        queue_manager.has_been_shuffled = True
        random.shuffle(queue)
        queue_manager.queues[today_str] = queue
        queue_manager.save_queues()

        titles = [entry.title for entry in queue]
        response = "Queue after shuffle:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
        await interaction.response.send_message(response)
        await send_now_playing(interaction, first_entry_before_shuffle)

    @app_commands.command(name='play_queue', description='Play the current queue.')
    async def play_queue(self, interaction: discord.Interaction):
        logging.debug("Play queue command executed")
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await interaction.response.send_message("Queue is empty, please add some tracks first.")
            return

        entry = queue[0] if queue else None
        if entry:
            if not interaction.guild.voice_client:
                if interaction.user.voice:
                    await interaction.user.voice.channel.connect()
                else:
                    await interaction.response.send_message("You are not connected to a voice channel.")
                    return

            await play_audio(interaction, entry)
        else:
            await interaction.response.send_message("Queue is empty.")

    @app_commands.command(name='list_queue', description='List all entries in the current queue.')
    async def list_queue(self, interaction: discord.Interaction):
        logging.debug("List queue command executed")
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
        else:
            titles = [entry.title for entry in queue]
            response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

            max_length = 2000
            chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

            for chunk in chunks:
                await interaction.response.send_message(chunk)
            await send_now_playing(interaction, queue_manager.currently_playing)

    @app_commands.command(name='remove_queue', description='Remove a track from the queue by index.')
    async def remove_queue(self, interaction: discord.Interaction, index: int):
        logging.debug(f"Remove queue command executed for index: {index}")
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
        adjusted_index = index - 1

        if 0 <= adjusted_index < len(queue):
            removed_entry = queue.pop(adjusted_index)
            queue_manager.save_queues()
            await interaction.response.send_message(f"Removed '{removed_entry.title}' from the queue.")
        else:
            await interaction.response.send_message("Invalid index. Please provide a valid index of the song to remove.")

    @app_commands.command(name='skip', description='Skip the current track.')
    async def skip(self, interaction: discord.Interaction):
        logging.debug("Skip command executed")
        date_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(date_str)
        if not queue:
            await interaction.response.send_message("Queue is empty.")
            return

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            current_entry = queue_manager.currently_playing
            if current_entry and not queue_manager.has_been_shuffled:
                queue.remove(current_entry)
                queue.append(current_entry)
                queue_manager.save_queues()

            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            # queue_manager.has_been_shuffled = False

    @app_commands.command(name='pause', description='Pause the currently playing track.')
    async def pause(self, interaction: discord.Interaction):
        logging.debug("Pause command executed")
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            message = await interaction.original_message()
            view = message.components[0].view
            view.paused = True
            view.update_buttons()
            await message.edit(view=view)
            await interaction.response.send_message('Playback paused.')
            logging.info("Playback paused.")
            print("Playback paused.")

    @app_commands.command(name='resume', description='Resume playback if it is paused.')
    async def resume(self, interaction: discord.Interaction):
        logging.debug("Resume command executed")
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            message = await interaction.original_message()
            view = message.components[0].view
            view.paused = False
            view.update_buttons()
            await message.edit(view=view)
            await interaction.response.send_message('Playback resumed.')
            logging.info("Playback resumed.")
            print("Playback resumed.")

    @app_commands.command(name='stop', description='Stop playback and disconnect the bot from the voice channel.')
    async def stop(self, interaction: discord.Interaction):
        logging.debug("Stop command executed")
        queue_manager.stop_is_triggered = True
        print(f'in the stop command function ------- {queue_manager.stop_is_triggered}')
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message('Playback stopped and disconnected.')
            logging.info("Playback stopped and bot disconnected.")
            print("Playback stopped and bot disconnected.")

    @app_commands.command(name='restart', description='Restart the currently playing track from the beginning.')
    async def restart(self, interaction: discord.Interaction):
        logging.debug("Restart command executed")
        if not queue_manager.currently_playing:
            await interaction.response.send_message("No track is currently playing.")
            return

        current_entry = queue_manager.currently_playing
        queue_manager.is_restarting = True

        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await play_audio(interaction, current_entry)

    @commands.command(name='mp3_list')
    async def play(self, ctx, url: str = None):
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not voice_client and ctx.author.voice:
            voice_client = await ctx.author.voice.channel.connect()
        elif not voice_client:
            await ctx.send("You are not connected to a voice channel.")
            return

        if ctx.message.attachments:
            first = True
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith('.mp3'):
                    file_path = await download_file(attachment.url, 'Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s')
                    if file_path:
                        entry = QueueEntry(
                            video_url=attachment.url,
                            best_audio_url=file_path,
                            title=attachment.filename,
                            is_playlist=False,
                            playlist_index=None
                        )
                        queue_manager.add_to_queue(entry)
                        await ctx.send(f"'{entry.title}' added to the queue.")
                        if first or not voice_client.is_playing():
                            await play_audio(ctx, entry)
                            first = False
            return

        elif url:
            if "list=" in url:
                playlist_length = await fetch_playlist_length(url)
                for index in range(1, playlist_length + 1):
                    video_info = await fetch_info(url, index=index)
                    if video_info and 'entries' in video_info:
                        video = video_info['entries'][0] if video_info['entries'] else None
                        if video:
                            entry = QueueEntry(
                                video_url=video['webpage_url'],
                                best_audio_url=next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), ''),
                                title=video['title'],
                                is_playlist=True,
                                playlist_index=index
                            )
                            queue_manager.add_to_queue(entry)
                            await ctx.send(f"Added to queue: {entry.title}")
                            if index == 1 or not voice_client.is_playing():
                                await play_audio(ctx, entry)
                    else:
                        await ctx.send(f"Failed to retrieve video at index {index}")
                        break
            else:
                entry = await process_single_video_or_mp3(url, ctx)
                if entry:
                    queue_manager.add_to_queue(entry)
                    await ctx.send(f"'{entry.title}' added to the queue.")
                    if not voice_client.is_playing():
                        await play_audio(ctx, entry)
            return
        else:
            await ctx.send("Please provide a valid URL or attach an MP3 file.")

def run_bot():
    logging.debug("Running bot")
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = AudioBot(command_prefix=".", intents=intents)

    @client.event
    async def on_ready():
        logging.debug("Bot is ready")
        await client.setup_hook()

    asyncio.run(client.add_cog(MusicCommands(client)))
    client.run(TOKEN)

if __name__=='__main__':
    run_bot()
