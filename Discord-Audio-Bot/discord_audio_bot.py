import json
import uuid
from datetime import datetime
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
import typing
from discord import Attachment

logging.basicConfig(level=logging.INFO, filename='queue_log.log', format='%(asctime)s:%(levelname)s:%(message)s')

class QueueEntry:
    def __init__(self, video_url: str, best_audio_url: str, title: str, is_playlist: bool, thumbnail: str = '', playlist_index: Optional[int] = None, duration: int = 0, is_favorited: bool = False, favorited_by: Optional[List[int]] = None):
        self.video_url = video_url
        self.best_audio_url = best_audio_url
        self.title = title
        self.is_playlist = is_playlist
        self.playlist_index = playlist_index
        self.thumbnail = thumbnail
        self.duration = duration
        self.is_favorited = is_favorited  # New property to indicate if the entry is favorited
        self.favorited_by = favorited_by if favorited_by is not None else []  # List of users who favorited the entry

    def to_dict(self):
        return {
            'video_url': self.video_url,
            'best_audio_url': self.best_audio_url,
            'title': self.title,
            'is_playlist': self.is_playlist,
            'playlist_index': self.playlist_index,
            'thumbnail': self.thumbnail,
            'is_favorited': self.is_favorited,  # Save favorite status
            'favorited_by': self.favorited_by  # Save list of users who favorited
        }

class BotQueue:
    def __init__(self):
        self.currently_playing = None
        self.queues = self.load_queues()
        self.ensure_today_queue_exists()
        self.last_played_audio = self.load_last_played_audio()
        self.is_restarting = False
        self.has_been_shuffled = False
        self.stop_is_triggered = False
        self.loop = False  # New property to manage looping


    def load_queues(self) -> Dict[str, List[QueueEntry]]:
        try:
            with open('queues.json', 'r') as file:
                queues_data = json.load(file)
            return {date: [QueueEntry(**entry) for entry in entries] for date, entries in queues_data.items()}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Failed to load queues: {e}")
            return {}

    def load_last_played_audio(self) -> Optional[str]:
        try:
            with open('last_played_audio.json', 'r') as file:
                return json.load(file).get('last_played_audio')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load last played audio: {e}")
            return None

    def save_queues(self):
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
        return info

async def fetch_playlist_length(url):
    ydl_opts = {'quiet': True, 'noplaylist': False, 'extract_entries': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
        return len(info.get('entries', []))

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename)

async def download_file(url: str, dest_folder: str) -> str:
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

async def play_audio(interaction, entry):
    queue_manager.currently_playing = entry
    queue_manager.save_queues()

    logging.info(f"Starting playback for: {entry.title} (URL: {entry.best_audio_url})")

    def after_playing(error):
        queue_manager.stop_is_triggered = False
        if error:
            logging.error(f"Error playing {entry.title}: {error}")
            asyncio.run_coroutine_threadsafe(interaction.channel.send("Error occurred during playback."), interaction.client.loop).result()
        else:
            logging.info(f"Finished playing {entry.title} at {datetime.now()}")
            if queue_manager.loop:
                logging.info(f"Looping {entry.title}")
                asyncio.run_coroutine_threadsafe(play_audio(interaction, entry), interaction.client.loop).result()
            else:
                if not queue_manager.is_restarting:
                    queue_manager.last_played_audio = entry.title
                queue_manager.save_queues()
                # asyncio.run_coroutine_threadsafe(disable_buttons(interaction, entry), interaction.client.loop).result()
                asyncio.run_coroutine_threadsafe(play_next(interaction), interaction.client.loop).result()

    async def start_playback():
        try:
            if interaction.guild.voice_client is None:
                logging.warning("Voice client is None. Attempting to connect.")
            elif not interaction.guild.voice_client.is_connected():
                logging.warning("Voice client is not connected. Attempting to reconnect.")
            elif interaction.guild.voice_client.is_playing():
                logging.warning("Voice client is already playing.")
            elif interaction.guild.voice_client.is_paused():
                logging.warning("Voice client is paused.")

            audio_source = discord.FFmpegPCMAudio(
                entry.best_audio_url,
                options='-bufsize 65536k -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -vn'
            )
            if not interaction.guild.voice_client.is_playing():
                interaction.guild.voice_client.play(audio_source, after=after_playing)
                await send_now_playing(interaction, entry)
                logging.info(f"Playback started for {entry.title} at {datetime.now()}")
        except Exception as e:
            if not queue_manager.stop_is_triggered:
                logging.error(f"Exception during playback: {e}")
                await interaction.channel.send(f"An error occurred during playback: {e}")
            if queue_manager.stop_is_triggered:
                print('do nothing')

    await start_playback()

async def send_now_playing(interaction, entry, paused=False):
    embed = discord.Embed(title="Now Playing", description=entry.title, url=entry.video_url)
    embed.set_thumbnail(url=entry.thumbnail)
    embed.add_field(name="URL", value=entry.video_url, inline=False)
    embed.add_field(name="Favorited by", value=', '.join([str(user_id) for user_id in entry.favorited_by]), inline=False)

    view = ButtonView(interaction.client, entry, paused=paused)
    message = await interaction.channel.send(embed=embed, view=view)
    await update_progress_bar(interaction, message, entry)

async def update_progress_bar(interaction, message, entry):
    duration = entry.duration if hasattr(entry, 'duration') else 300  # default to 5 minutes if duration is not available
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
    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    if queue and queue_manager.currently_playing:
        current_entry = queue_manager.currently_playing
        if current_entry in queue and not queue_manager.is_restarting:
            queue.remove(current_entry)
            queue.append(current_entry)
            queue_manager.save_queues()
        elif current_entry in queue and queue_manager.is_restarting:
            queue_manager.is_restarting = False
        if queue:
            entry = queue[0]
            await play_audio(interaction, entry)

async def process_play_command(interaction, url):
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
    if (playlist_length > 1):
        for index in range(2, playlist_length + 1):
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
                await interaction.response.send_message(f"Added to queue: {entry.title}")
            else:
                await interaction.channel.send(f"Failed to retrieve video at index {index}")
                await interaction.response.send_message(f"Failed to retrieve video at index {index}")

    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    titles = [entry.title for entry in queue]
    response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
    await interaction.response.send_message(response)

async def process_single_video_or_mp3(url, interaction):
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
    entry = QueueEntry(
        video_url=info.get('webpage_url', ''),
        best_audio_url=next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), ''),
        title=info.get('title', 'Unknown title'),
        is_playlist=False,
        thumbnail=info.get('thumbnail', '')
    )
    queue_manager.add_to_queue(entry)
    await play_audio(interaction, entry)

# async def disable_buttons(interaction, entry):
#     embed = discord.Embed(title="Now Playing", description=entry.title, url=entry.video_url)
#     embed.set_thumbnail(url=entry.thumbnail)
#     embed.add_field(name="URL", value=entry.video_url, inline=False)
#     embed.add_field(name="Favorited by", value=', '.join([str(user_id) for user_id in entry.favorited_by]), inline=False)

#     view = ButtonView(interaction.client, entry, paused=False, disable_all=True)
#     await interaction.message.edit(embed=embed, view=view)
async def disable_buttons(interaction, entry):
    message = await interaction.original_message()
    view = message.components[0].view
    view.disable_all_buttons()
    await message.edit(view=view)

class AudioBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix, intents=intents)

    async def setup_hook(self):
        # Initialize ButtonView with a dummy entry; this line can be adjusted as per your actual initialization logic
        dummy_entry = QueueEntry(video_url='', best_audio_url='', title='dummy', is_playlist=False)
        self.add_view(ButtonView(self, dummy_entry))
        await self.tree.sync()

    async def on_ready(self):
        logging.info(f'{self.user} is now connected and ready.')
        print(f'{self.user} is now connected and ready.')

class ButtonView(discord.ui.View):
    def __init__(self, bot, entry: QueueEntry, paused: bool = False):
        super().__init__(timeout=None)
        self.bot = bot
        self.paused = paused
        self.entry = entry  # Store the entry being played

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
        self.loop_button_id = f"loop-{uuid.uuid4()}"  # New loop button

        self.pause_button = discord.ui.Button(label="⏸️ Pause", style=discord.ButtonStyle.primary, custom_id=self.pause_button_id)
        self.resume_button = discord.ui.Button(label="▶️ Resume", style=discord.ButtonStyle.primary, custom_id=self.resume_button_id)
        self.stop_button = discord.ui.Button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id=self.stop_button_id)
        self.skip_button = discord.ui.Button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id=self.skip_button_id)
        self.restart_button = discord.ui.Button(label="🔄 Restart", style=discord.ButtonStyle.secondary, custom_id=self.restart_button_id)
        self.shuffle_button = discord.ui.Button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, custom_id=self.shuffle_button_id)
        self.list_queue_button = discord.ui.Button(label="📜 List Queue", style=discord.ButtonStyle.secondary, custom_id=self.list_queue_button_id)
        self.remove_button = discord.ui.Button(label="❌ Remove", style=discord.ButtonStyle.danger, custom_id=self.remove_button_id)
        self.previous_button = discord.ui.Button(label="⏮️ Previous", style=discord.ButtonStyle.secondary, custom_id=self.previous_button_id)
        self.loop_button = discord.ui.Button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id=self.loop_button_id)  # New loop button

        self.pause_button.callback = self.pause_button_callback
        self.resume_button.callback = self.resume_button_callback
        self.stop_button.callback = self.stop_button_callback
        self.skip_button.callback = self.skip_button_callback
        self.restart_button.callback = self.restart_button_callback
        self.shuffle_button.callback = self.shuffle_button_callback
        self.list_queue_button.callback = self.list_queue_button_callback
        self.remove_button.callback = self.remove_button_callback
        self.previous_button.callback = self.previous_button_callback
        self.loop_button.callback = self.loop_button_callback  # New loop button callback

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
        self.loop_button.label = "🔁 Looped" if queue_manager.loop else "🔁 Loop"  # Update loop button label
        self.add_item(self.loop_button)

    def disable_all_buttons(self):
        self.pause_button.disabled = True
        self.resume_button.disabled = True
        self.stop_button.disabled = True
        self.skip_button.disabled = True
        self.restart_button.disabled = True
        self.shuffle_button.disabled = True
        self.list_queue_button.disabled = True
        self.previous_button.disabled = True
        self.loop_button.disabled = True
        self.favorite_button.disabled = False  # Keep the favorite button active
        self.remove_button.disabled = False  # Keep the remove button active

        self.update_buttons()

    async def loop_button_callback(self, interaction: discord.Interaction):
        if queue_manager.currently_playing:
            queue_manager.loop = not queue_manager.loop
            self.loop_button.label = "🔁 Looped" if queue_manager.loop else "🔁 Loop"
            await interaction.response.send_message(f"Looping {'enabled' if queue_manager.loop else 'disabled'}.")
            logging.info(f"Looping {'enabled' if queue_manager.loop else 'disabled'} for {queue_manager.currently_playing.title}")
            self.update_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("No track is currently playing.", ephemeral=True)

    async def favorite_button_callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id in self.entry.favorited_by:
            self.entry.favorited_by.remove(user_id)
            self.entry.is_favorited = False
            self.favorite_button.style = discord.ButtonStyle.secondary  # Grey out the button
            self.favorite_button.label = "⭐ Favorite"
        else:
            self.entry.favorited_by.append(user_id)
            self.entry.is_favorited = True
            self.favorite_button.style = discord.ButtonStyle.primary  # Highlight the button
            self.favorite_button.label = "💛 Favorited"

        queue_manager.save_queues()
        await interaction.response.send_message(f"{'Added to' if self.entry.is_favorited else 'Removed from'} favorites.", ephemeral=True)
        await self.update_now_playing(interaction)

    async def update_now_playing(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Now Playing", description=self.entry.title, url=self.entry.video_url)
        embed.set_thumbnail(url=self.entry.thumbnail)
        embed.add_field(name="URL", value=self.entry.video_url, inline=False)
        embed.add_field(name="Favorited by", value=', '.join([str(user_id) for user_id in self.entry.favorited_by]), inline=False)

        await interaction.message.edit(embed=embed, view=self)

    async def pause_button_callback(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            self.paused = True
            self.update_buttons()
            await interaction.message.edit(view=self)
            await interaction.response.send_message('Playback paused.', ephemeral=True)

    async def resume_button_callback(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            self.paused = False
            self.update_buttons()
            await interaction.message.edit(view=self)
            await interaction.response.send_message('Playback resumed.', ephemeral=True)

    async def stop_button_callback(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            queue_manager.stop_is_triggered = True
            interaction.guild.voice_client.stop()
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message('Playback stopped and disconnected.', ephemeral=True)

    async def skip_button_callback(self, interaction: discord.Interaction):
        date_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(date_str)
        if not queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            current_entry = queue_manager.currently_playing
            if current_entry and not queue_manager.has_been_shuffled:
                queue.remove(current_entry)
                queue.append(current_entry)
                queue_manager.save_queues()

            queue_manager.has_been_shuffled = False
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await interaction.response.send_message("Skipped the current track.", ephemeral=True)

    async def restart_button_callback(self, interaction: discord.Interaction):
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
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return
        first_entry_before_shuffle  = queue_manager.currently_playing

        queue_manager.has_been_shuffled = True
        random.shuffle(queue)
        queue_manager.queues[today_str] = queue
        queue_manager.save_queues()

        titles = [entry.title for entry in queue]
        response = "Queue after shuffle:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
        await interaction.response.send_message(response)
        await self.update_now_playing(interaction)

    async def list_queue_button_callback(self, interaction: discord.Interaction):
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
            await self.update_now_playing(interaction)

    async def remove_button_callback(self, interaction: discord.Interaction):
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
            await self.update_now_playing(interaction)

### 3. Modify the `send_now_playing` method:
# Reflect the favorite status in the embed message and update the button color.

async def send_now_playing(interaction, entry, paused=False):
    embed = discord.Embed(title="Now Playing", description=entry.title, url=entry.video_url)
    embed.set_thumbnail(url=entry.thumbnail)
    embed.add_field(name="URL", value=entry.video_url, inline=False)
    embed.add_field(name="Favorited by", value=', '.join([str(user_id) for user_id in entry.favorited_by]), inline=False)

    view = ButtonView(interaction.client, entry, paused=paused)
    message = await interaction.channel.send(embed=embed, view=view)
    await update_progress_bar(interaction, message, entry)

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name='loop', description='Toggle looping of the current track.')
    async def loop(self, interaction: discord.Interaction):
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
        help_text = """
        Here are the commands you can use:

        **/play [URL or attachment]** - Play audio from a YouTube URL or attached MP3 file.
        **/play_video [title]** - Plays the video by title from the queue.
        **/shuffle** - Randomly shuffles the queue and shows the new order.
        **/list_queue** - Lists all entries currently in the queue.
        **/play_queue** - Starts playing the queue from the first track.
        **/remove_by_title [title]** - Removes a specific track by title from the queue.
        **/skip** - Skips the current track and plays the next one in the queue.
        **/pause** - Pauses the currently playing track.
        **/resume** - Resumes playback if it's paused.
        **/stop** - Stops playback and disconnects the bot from the voice channel.
        **/previous** - Plays the last entry that was being played.
        **/restart** - Restarts the currently playing track from the beginning.
        
        **Always taking suggestions for the live service of Radio-Bot**

        Type a command to execute it. For example: `/play https://youtube.com/watch?v=example`
        """
        await interaction.response.send_message(help_text)

    @app_commands.command(name='play_video', description='Play a video from the queue by title.')
    async def play_video(self, interaction: discord.Interaction, title: str):
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
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return
        first_entry_before_shuffle  = queue_manager.currently_playing

        queue_manager.has_been_shuffled = True
        random.shuffle(queue)
        queue_manager.queues[today_str] = queue
        queue_manager.save_queues()

        titles = [entry.title for entry in queue]
        response = "Queue after shuffle:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
        await interaction.response.send_message(response)
        await self.send_now_playing(interaction, first_entry_before_shuffle)

    @app_commands.command(name='play_queue', description='Play the current queue.')
    async def play_queue(self, interaction: discord.Interaction):
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

    @app_commands.command(name='remove_queue', description='Remove a track from the queue by index.')
    async def remove_queue(self, interaction: discord.Interaction, index: int):
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
        if 0 <= index < len(queue):
            removed_entry = queue.pop(index)
            queue_manager.save_queues()
            await interaction.response.send_message(f"Removed '{removed_entry.title}' from the queue.")
        else:
            await interaction.response.send_message("Invalid index. Please provide a valid index of the song to remove.")

    @app_commands.command(name='skip', description='Skip the current track.')
    async def skip(self, interaction: discord.Interaction):
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

            queue_manager.has_been_shuffled = False
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)

    @app_commands.command(name='pause', description='Pause the currently playing track.')
    async def pause(self, interaction: discord.Interaction):
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
        if not queue_manager.currently_playing:
            await interaction.response.send_message("No track is currently playing.")
            return

        current_entry = queue_manager.currently_playing
        queue_manager.is_restarting = True

        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await play_audio(interaction, current_entry)

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = AudioBot(command_prefix=".", intents=intents)

    @client.event
    async def on_ready():
        await client.setup_hook()

    asyncio.run(client.add_cog(MusicCommands(client)))
    client.run(TOKEN)

if __name__ == '__main__':
    run_bot()
