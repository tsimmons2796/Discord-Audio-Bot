import aiohttp
import asyncio
import json
import logging
import os
import random
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import discord
from discord import app_commands, Attachment
from discord.errors import NotFound
from discord.ext import commands
from discord.interactions import Interaction
from discord.ui import Button, Select, View
from dotenv import load_dotenv
from lyricsgenius import Genius
from mutagen.id3 import APIC, ID3, TIT2, TPE1
from mutagen.mp3 import MP3
from youtubesearchpython import VideosSearch
import yt_dlp

load_dotenv()

# Access the Genius API token
GENIUS_API_TOKEN = os.getenv('genius_api_token')

# Initialize the Genius API client
genius = Genius(GENIUS_API_TOKEN)

logging.basicConfig(level=logging.DEBUG, filename='queue_log.log', format='%(asctime)s:%(levelname)s:%(message)s')
# Do not remove any of the logs or print statements. Only add new ones if and where needed, especially when adding new code.

UNWANTED_PATTERNS = [
    r'\(Official Video\)', 
    r'\(Official Audio\)', 
    r'\(Official Lyric Video\)', 
    r'\(Visualizer\)', 
    r'\(audio only\)', 
    r'\(Official Music Video\)', 
    r'\[Official Visualizer\]',
    r'\(Lyrics\)',
    r'\(Lyric Video\)',
    r'\[Lyrics\]',
    r'\(HD\)',
    r'\[HD\]',
    r'\[ Official Music Video \]',
    r'\[ Official Visualizer \]',
    r'\[ Visualizer \]',
    # Add more patterns as needed
]

def sanitize_title(title: str) -> str:
    """
    Sanitize the given title by removing unwanted characters and patterns.

    Args:
        title (str): The original title of the song.

    Returns:
        str: The sanitized title.
    """
    logging.debug(f"Sanitizing title: {title}")
    print(f"Sanitizing title: {title}")
    # Define a pattern to match characters that are not allowed in file names.
    illegal_characters_pattern = r'[<>:"/\\|?*]'
    
    # Remove illegal characters from the title.
    sanitized_title = re.sub(illegal_characters_pattern, '', title, flags=re.IGNORECASE)
    logging.debug(f"Title after removing illegal characters: {sanitized_title}")
    print(f"Title after removing illegal characters: {sanitized_title}")
    
    # Remove unwanted patterns defined in UNWANTED_PATTERNS from the title.
    for unwanted_pattern in UNWANTED_PATTERNS:
        sanitized_title = re.sub(unwanted_pattern, '', sanitized_title, flags=re.IGNORECASE).strip()
        logging.debug(f"Title after removing pattern '{unwanted_pattern}': {sanitized_title}")
        print(f"Title after removing pattern '{unwanted_pattern}': {sanitized_title}")
    
    return sanitized_title

class QueueEntry:
    def __init__(self, video_url: str, best_audio_url: str, title: str, is_playlist: bool, thumbnail: str = '', playlist_index: Optional[int] = None, duration: int = 0, is_favorited: bool = False, favorited_by: Optional[List[Dict[str, str]]] = None, has_been_arranged: bool = False, has_been_played_after_arranged: bool = False, timestamp: Optional[str] = None, paused_duration: Optional[float] = 0.0, guild: Optional[discord.Guild] = None):
        logging.debug(f"Creating QueueEntry: {title}, URL: {video_url}")
        logging.debug(f"Creating QueueEntry: {title}, URL: {video_url}, Guild: {guild}")
        print(f"Creating QueueEntry: {title}, URL: {video_url}, Guild: {guild}")
        self.video_url = video_url
        self.best_audio_url = best_audio_url
        self.title = sanitize_title(title)  # Sanitize title here
        self.is_playlist = is_playlist
        self.playlist_index = playlist_index
        self.thumbnail = thumbnail
        self.duration = duration
        self.is_favorited = is_favorited
        self.favorited_by = favorited_by if favorited_by is not None else []
        self.has_been_arranged = has_been_arranged
        self.has_been_played_after_arranged = has_been_played_after_arranged  # New property
        self.timestamp = timestamp or datetime.now().isoformat()
        self.pause_start_time = None
        self.start_time = datetime.now()
        self.paused_duration = timedelta(seconds=paused_duration) if isinstance(paused_duration, (int, float)) else timedelta(seconds=0.0)
        self.guild = guild  # Ensure guild is set here

    def to_dict(self):
        logging.debug(f"Converting QueueEntry to dict: {self.title}")
        print(f"Converting QueueEntry to dict: {self.title}")
        return {
            'video_url': self.video_url,
            'best_audio_url': self.best_audio_url,
            'title': self.title,
            'is_playlist': self.is_playlist,
            'playlist_index': self.playlist_index,
            'thumbnail': self.thumbnail,
            'duration': self.duration,
            'is_favorited': self.is_favorited,
            'favorited_by': self.favorited_by,
            'has_been_arranged': self.has_been_arranged,
            'has_been_played_after_arranged': self.has_been_played_after_arranged,  # New property
            'timestamp': self.timestamp,
            'paused_duration': self.paused_duration.total_seconds()
        }

    async def refresh_url(self):
        logging.debug(f"Refreshing URL for: {self.title}")
        print(f"Refreshing URL for: {self.title}")
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
                    self.duration = info.get('duration', 0)  # Update duration
                    self.timestamp = datetime.now().isoformat()  # Update the timestamp after refreshing
                    logging.info(f"URL refreshed for {self.title}. New URL: {self.best_audio_url}, Duration: {self.duration}")
                    print(f"URL refreshed for {self.title}. New URL: {self.best_audio_url}, Duration: {self.duration}")

class BotQueue:
    def __init__(self):
        logging.debug("Initializing BotQueue")
        print("Initializing BotQueue")
        self.queue_file = 'queue.json'  # Ensure this path is correct
        self.currently_playing = None
        self.queues = self.load_queues()
        self.queue_cache = {}
        self.last_played_audio = self.load_last_played_audio()
        self.is_restarting = False
        self.has_been_shuffled = False
        self.stop_is_triggered = False
        self.loop = False

    def load_queues(self) -> Dict[str, List[QueueEntry]]:
        try:
            with open('queues.json', 'r') as file:
                queues_data = json.load(file)
                logging.info("Queues loaded successfully")
                print("Queues loaded successfully")
                return {server_id: [QueueEntry(**entry) for entry in entries] for server_id, entries in queues_data.items()}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Failed to load queues: {e}")
            print(f"Failed to load queues: {e}")
            return {}

    def load_last_played_audio(self) -> Dict[str, Optional[str]]:
        logging.debug("Loading last played audio from file")
        print("Loading last played audio from file")
        try:
            with open('last_played_audio.json', 'r') as file:
                data = json.load(file)
                logging.info("Last played audio loaded successfully")
                print("Last played audio loaded successfully")
                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load last played audio: {e}")
            print(f"Failed to load last played audio: {e}")
            return {}

    def save_queues(self):
        logging.debug("Saving queues to file")
        print("Saving queues to file")
        try:
            with open('queues.json', 'w') as file:
                json.dump({k: [entry.to_dict() for entry in v] for k, v in self.queues.items()}, file, indent=4)
                logging.info("Queues saved successfully")
                print("Queues saved successfully")
            with open('last_played_audio.json', 'w') as file:
                json.dump(self.last_played_audio, file, indent=4)
                logging.info("Last played audio saved successfully")
                print("Last played audio saved successfully")
            self.queue_cache = self.queues.copy()  # Update cache when saving
        except Exception as e:
            logging.error(f"Failed to save queues or last played audio: {e}")
            print(f"Failed to save queues or last played audio: {e}")

    def get_queue(self, server_id: str) -> List[QueueEntry]:
        logging.debug(f"Getting queue for server: {server_id}")
        print(f"Getting queue for server: {server_id}")
        if server_id in self.queue_cache:
            return self.queue_cache[server_id]
        else:
            queue = self.queues.get(server_id, [])
            self.queue_cache[server_id] = queue
            return queue

    def add_to_queue(self, server_id: str, entry: QueueEntry):
        logging.debug(f"Adding {entry.title} to queue for server {server_id}")
        print(f"Adding {entry.title} to queue for server {server_id}")
        if server_id not in self.queues:
            self.queues[server_id] = []
        self.queues[server_id].append(entry)
        self.queue_cache[server_id] = self.queues[server_id]  # Update cache
        self.save_queues()
        logging.info(f"Added {entry.title} to queue for server {server_id}")
        print(f"Added {entry.title} to queue for server {server_id}")

    def ensure_queue_exists(self, server_id: str):
        logging.debug(f"Ensuring queue exists for server: {server_id}")
        print(f"Ensuring queue exists for server: {server_id}")
        if server_id not in self.queues:
            self.queues[server_id] = []
            self.queue_cache[server_id] = self.queues[server_id]  # Update cache
            self.save_queues()
            logging.info(f"Ensured queue exists for server: {server_id}")
            print(f"Ensured queue exists for server: {server_id}")

queue_manager = BotQueue()
executor = ThreadPoolExecutor(max_workers=1)

async def fetch_info(url, index: int = None):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': False if "list=" in url else True,
        'playlist_items': str(index) if index is not None else None,
        'ignoreerrors': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.debug(f"Fetching info for URL: {url}, index: {index}")
            print(f"Fetching info for URL: {url}, index: {index}")
            info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
            if 'entries' in info:
                entries = []
                for entry in info['entries']:
                    if entry and not entry.get('is_unavailable', False):  # Ensure the entry is valid and available
                        entry['duration'] = entry.get('duration', 0)
                        entry['thumbnail'] = entry.get('thumbnail', '')
                        entry['best_audio_url'] = next((f['url'] for f in entry['formats'] if f.get('acodec') != 'none'), entry.get('url'))
                        entries.append(entry)
                        logging.debug(f"Processing entry: {entry.get('title', 'Unknown title')}")
                        print(f"Processing entry: {entry.get('title', 'Unknown title')}")
                info['entries'] = entries
            else:
                info['duration'] = info.get('duration', 0)
                info['thumbnail'] = info.get('thumbnail', '')
                info['best_audio_url'] = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), info.get('url'))
                logging.debug(f"Processing entry: {info.get('title', 'Unknown title')}")
                print(f"Processing entry: {info.get('title', 'Unknown title')}")
            return info
    except yt_dlp.utils.ExtractorError as e:
        logging.warning(f"Skipping unavailable video: {str(e)}")
        print(f"Skipping unavailable video: {str(e)}")
        return None

async def fetch_playlist_length(url):
    ydl_opts = {'quiet': True, 'noplaylist': False, 'extract_entries': True, 'ignoreerrors': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.debug(f"Fetching playlist length for URL: {url}")
            print(f"Fetching playlist length for URL: {url}")
            info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
            length = len(info.get('entries', []))
            logging.info(f"Playlist length: {length}")
            print(f"Playlist length: {length}")
            return length
    except yt_dlp.utils.ExtractorError as e:
        logging.warning(f"Error fetching playlist length: {str(e)}")
        print(f"Error fetching playlist length: {str(e)}")
        return 0

def sanitize_filename(filename: str) -> str:
    logging.debug(f"Sanitizing filename: {filename}")
    print(f"Sanitizing filename: {filename}")
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename)

async def download_file(url: str, dest_folder: str) -> str:
    logging.debug(f"Downloading file from URL: {url}")
    print(f"Downloading file from URL: {url}")
    os.makedirs(dest_folder, exist_ok=True)
    filename = sanitize_filename(os.path.basename(url))
    file_path = os.path.join(dest_folder, filename)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    f.write(await response.read())
                logging.info(f"Downloaded file: {file_path}")
                print(f"Downloaded file: {file_path}")
                return file_path
            else:
                logging.error(f"Failed to download file: {url}")
                print(f"Failed to download file: {url}")
                return None

async def get_lyrics(query: str) -> str:
    def process_lyrics(lyrics: str) -> str:
        lyrics = re.sub(r'(?i).*Lyrics', 'Lyrics', lyrics, count=1, flags=re.IGNORECASE).strip()
        lyrics = re.sub(r'(?i)Embed.*$', '', lyrics, flags=re.IGNORECASE).strip()
        if re.match(r'(?i)lyrics', lyrics[:15]):
            lyrics = re.sub(r'(?i)lyrics', '', lyrics, count=1).strip()
        return lyrics

    def validate_lyrics(lyrics: str, title: str, artist: str) -> bool:
        return title.lower() in lyrics.lower() and any(artist_part.lower() in song.artist.lower() for artist_part in artist.split())

    try:
        artist, title = None, None
        print(f"Original query: {query}")
        possible_splits = re.split(r' - | by | from | @ | \| ', query, maxsplit=1)
        print(f"Possible splits: {possible_splits}")

        if len(possible_splits) == 2:
            artist, title = possible_splits
            print(f"Extracted artist: {artist.strip()}, title: {title.strip()}")
            song = genius.search_song(title.strip(), artist.strip())
            if song:
                lyrics = process_lyrics(song.lyrics)
                print(f"Lyrics after processing:\n{lyrics}")
                if validate_lyrics(lyrics, title.strip(), artist.strip()):
                    print(f"Lyrics found for {artist.strip()} - {title.strip()}")
                    return f"Lyrics for {artist.strip()} - {title.strip()}\n\n{lyrics}"
                # else:
                #     print(f"Lyrics not found for {title.strip()} by {artist.strip()}")
                #     return f"Lyrics not found for {title.strip()} by {artist.strip()}"

        print(f"Searching with the entire query: {query}")
        song = genius.search_song(query)
        if song:
            lyrics = process_lyrics(song.lyrics)
            print(f"Lyrics after processing:\n{lyrics}")
            if validate_lyrics(lyrics, song.title, song.artist):
                print(f"Lyrics found for {song.artist} - {song.title}")
                return f"Lyrics for {song.artist} - {song.title}\n\n{lyrics}"
            else:
                print(f"Lyrics not found for {song.title} by {song.artist}")
                return f"Lyrics not found for {song.title} by {song.artist}"

        print("Lyrics not found.")
        return "Lyrics not found."
    except Exception as e:
        logging.error(f"Error fetching lyrics: {e}")
        print(f"Exception: {e}")
        return "An error occurred while fetching the lyrics."

def extract_mp3_metadata(file_path: str) -> dict:
    """
    Extract metadata from the given MP3 file.

    Args:
        file_path (str): The path to the MP3 file.

    Returns:
        dict: A dictionary containing the title, thumbnail, and duration of the MP3 file.
    """
    logging.debug(f"Extracting metadata from MP3 file: {file_path}")
    print(f"Extracting metadata from MP3 file: {file_path}")
    try:
        audio = MP3(file_path, ID3=ID3)
        
        # Extract title and artist from the MP3 tags.
        title = audio.tags.get('TIT2', None)
        artist = audio.tags.get('TPE1', None)
        thumbnail = None
        
        # Use the file name if title is not found in the tags.
        if not title:
            title = os.path.basename(file_path).replace('_', ' ')
            title = title.rsplit('.mp3', 1)[0]
        else:
            title = title.text[0]
        
        if not artist:
            artist = ''
        else:
            artist = artist.text[0]
        
        # Extract album art if available.
        if 'APIC:' in audio.tags:
            apic = audio.tags['APIC:']
            thumbnail = apic.data
        
        # Extract the duration of the MP3 file.
        duration = int(audio.info.length) if audio.info else 0
        
        return {
            'title': f"{artist} - {title}".strip(' - '),
            'thumbnail': thumbnail,
            'duration': duration
        }
    except Exception as e:
        logging.error(f"Error extracting metadata from {file_path}: {e}")
        print(f"Error extracting metadata from {file_path}: {e}")
        return {
            'title': os.path.basename(file_path).replace('_', ' ').split('.mp3', 1)[0],
            'thumbnail': None,
            'duration': 0
        }

async def play_audio(ctx_or_interaction, entry):
    try:
        server_id = str(ctx_or_interaction.guild.id)
        ensure_queue_exists(server_id)

        await refresh_url_if_needed(entry)
        entry.guild = ctx_or_interaction.guild  # Ensure guild is set
        if entry.duration == 0:
            await update_entry_duration(entry)

        set_currently_playing(entry)

        logging.info(f"Starting playback for: {entry.title} (URL: {entry.best_audio_url})")

        def after_playing_callback(error):
            handle_playback_end(ctx_or_interaction, entry, error)

        await start_playback(ctx_or_interaction, entry, after_playing_callback)

        if isinstance(ctx_or_interaction, discord.Interaction):
            await send_now_playing_message(ctx_or_interaction, entry)

        # Schedule a halfway point queue refresh
        halfway_duration = entry.duration / 2
        asyncio.create_task(schedule_halfway_queue_refresh(server_id, halfway_duration))
    except Exception as e:
        await handle_playback_exception(ctx_or_interaction, entry, e)

async def schedule_halfway_queue_refresh(server_id, delay):
    await asyncio.sleep(delay)
    queue_manager.get_queue(server_id)
    logging.debug(f"Queue refreshed at halfway point for server {server_id}")
    print(f"Queue refreshed at halfway point for server {server_id}")

def handle_playback_end(ctx_or_interaction, entry, error):
    queue_manager.stop_is_triggered = False
    if error:
        logging.error(f"Error playing {entry.title}: {error}")
        print(f"Error playing {entry.title}: {error}")
        bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.bot
        asyncio.run_coroutine_threadsafe(ctx_or_interaction.channel.send("Error occurred during playback."), bot_client.loop).result()
    else:
        logging.info(f"Finished playing {entry.title} at {datetime.now()}")
        print(f"Finished playing {entry.title} at {datetime.now()}")
        manage_queue_after_playback(ctx_or_interaction, entry)

def ensure_queue_exists(server_id):
    queue_manager.ensure_queue_exists(server_id)

async def refresh_url_if_needed(entry):
    entry_timestamp = datetime.fromisoformat(entry.timestamp)
    if datetime.now() - entry_timestamp > timedelta(hours=3):
        await entry.refresh_url()

async def update_entry_duration(entry):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'ignoreerrors': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.get_running_loop().run_in_executor(None, lambda: ydl.extract_info(entry.video_url, download=False))
        if info:
            entry.duration = info.get('duration', 0)
            queue_manager.save_queues()
            logging.info(f"Updated duration for {entry.title}: {entry.duration} seconds")

def set_currently_playing(entry):
    entry.start_time = datetime.now()
    entry.paused_duration = timedelta(0)
    queue_manager.currently_playing = entry
    queue_manager.save_queues()

async def start_playback(ctx_or_interaction, entry, after_callback):
    try:
        logging.debug("Starting playback")
        print("Starting playback")
        voice_client = ctx_or_interaction.guild.voice_client
        if queue_manager.stop_is_triggered:
            logging.info("Playback stopped before starting")
            print("Playback stopped before starting")
            return

        if voice_client is None:
            logging.error("No voice client found.")
            print("No voice client found.")
            return

        audio_source = discord.FFmpegPCMAudio(
            entry.best_audio_url,
            options='-bufsize 65536k -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -vn'
        )
        if not voice_client.is_playing():
            voice_client.play(audio_source, after=after_callback)
            asyncio.create_task(send_now_playing(ctx_or_interaction, entry))
            queue_manager.has_been_shuffled = False
            logging.info(f"Playback started for {entry.title} at {datetime.now()}")
            print(f"Playback started for {entry.title} at {datetime.now()}")
    except Exception as e:
        if not queue_manager.stop_is_triggered:
            logging.error(f"Exception during playback: {e}")
            print(f"Exception during playback: {e}")
            bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.bot
            await ctx_or_interaction.channel.send(f"An error occurred during playback: {e}")

def after_playing(ctx_or_interaction, entry):
    def after_playing_callback(error):
        queue_manager.stop_is_triggered = False
        if error:
            logging.error(f"Error playing {entry.title}: {error}")
            print(f"Error playing {entry.title}: {error}")
            bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.bot
            asyncio.run_coroutine_threadsafe(ctx_or_interaction.channel.send("Error occurred during playback."), bot_client.loop).result()
        else:
            logging.info(f"Finished playing {entry.title} at {datetime.now()}")
            print(f"Finished playing {entry.title} at {datetime.now()}")
            manage_queue_after_playback(ctx_or_interaction, entry)
    return after_playing_callback

def manage_queue_after_playback(ctx_or_interaction, entry):
    if not queue_manager.is_restarting and not queue_manager.has_been_shuffled and not queue_manager.loop:
        queue = queue_manager.get_queue(str(ctx_or_interaction.guild.id))
        if entry in queue:
            if entry.has_been_arranged and entry.has_been_played_after_arranged:
                entry.has_been_arranged = False
                entry.has_been_played_after_arranged = False
                queue.remove(entry)
                queue.append(entry)
            elif entry.has_been_arranged and not entry.has_been_played_after_arranged:
                entry.has_been_played_after_arranged = True
            queue_manager.save_queues()

    if queue_manager.loop:
        logging.info(f"Looping {entry.title}")
        print(f"Looping {entry.title}")
        bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.bot
        asyncio.run_coroutine_threadsafe(play_audio(ctx_or_interaction, entry), bot_client.loop).result()
    else:
        if not queue_manager.is_restarting:
            queue_manager.last_played_audio[str(ctx_or_interaction.guild.id)] = entry.title
        queue_manager.save_queues()
        bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.bot
        asyncio.run_coroutine_threadsafe(play_next(ctx_or_interaction), bot_client.loop).result()

async def update_all_now_playing_messages(ctx_or_interaction, entry):
    for message_id in (ctx_or_interaction.client if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.bot).now_playing_messages:
        try:
            message = await ctx_or_interaction.channel.fetch_message(message_id)
            view = ButtonView(ctx_or_interaction.client if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.bot, entry)
            await message.edit(view=view)
        except Exception as e:
            logging.error(f"Error updating view for message {message_id}: {e}")
            print(f"Error updating view for message {message_id}: {e}")

async def handle_playback_exception(ctx_or_interaction, entry, e):
    logging.error(f"Exception in play_audio: {e}")
    if isinstance(ctx_or_interaction, discord.Interaction):
        try:
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(f"An error occurred: {e}")
        except NotFound as e:
            logging.error(f"Webhook not found: {e}")
            await ctx_or_interaction.channel.send(f"An error occurred: {e}")
    else:
        await ctx_or_interaction.send(f"An error occurred: {e}")

    await update_all_now_playing_messages(ctx_or_interaction, entry)


async def send_now_playing_message(ctx_or_interaction, entry):
    if isinstance(ctx_or_interaction, discord.Interaction):
        try:
            if not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(f"Now playing: {entry.title}")
        except NotFound as e:
            logging.error(f"Webhook not found: {e}")
            await ctx_or_interaction.channel.send(f"Now playing: {entry.title}")


async def send_now_playing(ctx_or_interaction, entry, paused=False):
    logging.debug(f"Sending now playing message for: {entry.title}")
    print(f"Sending now playing message for: {entry.title}")

    embed = create_now_playing_embed(entry)
    view = ButtonView(ctx_or_interaction.client, entry, paused=paused, current_user=ctx_or_interaction.user)
    message = await ctx_or_interaction.channel.send(embed=embed, view=view)

    if not paused and not queue_manager.currently_playing:
        entry.start_time = datetime.now()

    await schedule_progress_bar_update(ctx_or_interaction, message, entry)

    store_message_info(ctx_or_interaction.client, message.id, view)

    logging.debug(f"Now playing message sent with ID: {message.id}")
    print(f"Now playing message sent with ID: {message.id}")

def create_now_playing_embed(entry):
    embed = discord.Embed(title="Now Playing", description=entry.title, url=entry.video_url)
    embed.set_thumbnail(url=entry.thumbnail)

    favorited_by = ', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else "No one"
    embed.add_field(name="Favorited by", value=favorited_by, inline=False)

    duration = entry.duration if hasattr(entry, 'duration') else 300
    progress_bar, elapsed_str, duration_str = create_progress_bar(0, duration)
    embed.add_field(name="Progress", value=f"{progress_bar} {elapsed_str} / {duration_str}", inline=False)

    return embed

def store_message_info(bot, message_id, view):
    bot.message_views[message_id] = view
    bot.add_now_playing_message(message_id)

async def schedule_progress_bar_update(ctx_or_interaction, message, entry):
    await update_progress_bar(ctx_or_interaction, message, entry)
    asyncio.create_task(update_progress_bar(ctx_or_interaction, message, entry))

def create_progress_bar(progress, duration):
    total_blocks = 20
    filled_blocks = int(progress * total_blocks)
    progress_bar = "[" + "=" * filled_blocks + " " * (total_blocks - filled_blocks) + "]"
    elapsed_str = str(timedelta(seconds=int(progress * duration)))
    duration_str = str(timedelta(seconds=duration))
    return progress_bar, elapsed_str, duration_str

async def update_progress_bar(interaction, message, entry):
    logging.debug(f"Updating progress bar for: {entry.title}")
    duration = entry.duration if hasattr(entry, 'duration') else 300

    while True:
        if not is_entry_currently_playing(entry):
            logging.info(f"Stopping progress update for {entry.title}")
            break

        if not is_playback_active(interaction):
            await finalize_progress_update(interaction, message, entry, duration)
            break

        await refresh_progress_bar(interaction, message, entry, duration)
        await asyncio.sleep(1)  # Update less frequently to reduce load

def is_entry_currently_playing(entry):
    return queue_manager.currently_playing == entry

def is_playback_active(interaction):
    return interaction.guild.voice_client and interaction.guild.voice_client.is_playing()

async def finalize_progress_update(interaction, message, entry, duration):
    elapsed = calculate_elapsed_time(entry, duration)
    progress_bar, elapsed_str, duration_str = create_progress_bar(elapsed / duration, duration)
    embed = update_embed_fields(message.embeds[0], entry, progress_bar, elapsed_str, duration_str)
    view = ButtonView(interaction.client, entry, paused=False, current_user=interaction.user)
    await message.edit(embed=embed, view=view)

async def refresh_progress_bar(interaction, message, entry, duration):
    elapsed = calculate_elapsed_time(entry, duration)
    progress_bar, elapsed_str, duration_str = create_progress_bar(elapsed / duration, duration)
    embed = update_embed_fields(message.embeds[0], entry, progress_bar, elapsed_str, duration_str)
    view = ButtonView(interaction.client, entry, paused=False, current_user=interaction.user)
    await message.edit(embed=embed, view=view)

def calculate_elapsed_time(entry, duration):
    elapsed = (datetime.now() - entry.start_time - entry.paused_duration).total_seconds()
    return min(elapsed, duration)

def update_embed_fields(embed, entry, progress_bar, elapsed_str, duration_str):
    favorited_by = ', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else "No one"
    embed.set_field_at(0, name="Favorited by", value=favorited_by, inline=False)
    embed.set_field_at(1, name="Progress", value=f"{progress_bar} {elapsed_str} / {duration_str}", inline=False)
    return embed

async def check_for_next_entry_refresh(interaction, entry, duration):
    elapsed = calculate_elapsed_time(entry, duration)
    if duration - elapsed <= 30:
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if len(queue) > 1:
            next_entry = queue[1]
            if datetime.now() - datetime.fromisoformat(next_entry.timestamp) > timedelta(hours=3):
                await next_entry.refresh_url()

async def play_next_entry_in_queue(interaction, queue):
    if queue:
        entry = queue[0]
        await play_audio(interaction, entry)

async def play_next(interaction):
    logging.debug("Playing next track in the queue")
    print("Playing next track in the queue")
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    
    if queue and queue_manager.currently_playing:
        current_entry = queue_manager.currently_playing
        check_and_arrange_current_entry(queue, current_entry)
        
        queue_manager.is_restarting = False
        await play_next_entry_in_queue(interaction, queue)

def check_and_arrange_current_entry(queue, current_entry):
    if current_entry in queue and not queue_manager.is_restarting:
        if not current_entry.has_been_arranged and not queue_manager.has_been_shuffled:
            queue.remove(current_entry)
            queue.append(current_entry)
        queue_manager.save_queues()

async def fetch_first_video_info(url):
    first_video_info = await fetch_info(url, index=1)
    if not first_video_info or 'entries' not in first_video_info or not first_video_info['entries']:
        return None
    return first_video_info['entries'][0]

def create_queue_entry(video_info, index):
    logging.debug(f"Creating QueueEntry from video_info: {video_info.get('title', 'Unknown title')}")
    print(f"Creating QueueEntry from video_info: {video_info.get('title', 'Unknown title')}")
    return QueueEntry(
        video_url=video_info.get('webpage_url', ''),
        best_audio_url=video_info.get('best_audio_url', ''),
        title=video_info.get('title', 'Unknown title'),
        is_playlist=True,
        thumbnail=video_info.get('thumbnail', ''),
        playlist_index=index,
        duration=video_info.get('duration', 0)
    )

async def send_queue_update(interaction, server_id):
    queue = queue_manager.get_queue(server_id)
    titles = [entry.title for entry in queue]
    response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
    logging.debug(response)
    print(response)
    await interaction.followup.send(response)

async def process_play_command(interaction, url):
    server_id = str(interaction.guild.id)
    first_video = await fetch_first_video_info(url)
    if not first_video:
        await interaction.followup.send("Could not retrieve the first video of the playlist.")
        return

    first_entry = create_queue_entry(first_video, 1)
    if not queue_manager.currently_playing:
        queue_manager.queues[server_id].insert(0, first_entry)
        await play_audio(interaction, first_entry)
    else:
        queue_manager.add_to_queue(server_id, first_entry)
    
    await interaction.followup.send(f"Added to queue: {first_entry.title}")

    if not queue_manager.currently_playing:
        await play_audio(interaction, first_entry)

    asyncio.create_task(process_rest_of_playlist(interaction, url, server_id))

async def process_rest_of_playlist(interaction, url, server_id):
    playlist_length = await fetch_playlist_length(url)
    if playlist_length > 1:
        for index in range(2, playlist_length + 1):
            try:
                info = await fetch_info(url, index=index)
                if info and 'entries' in info and info['entries']:
                    video = info['entries'][0]
                    if video.get('is_unavailable', False):
                        logging.warning(f"Skipping unavailable video at index {index}")
                        await interaction.followup.send(f"Skipping unavailable video at index {index}")
                        continue
                    entry = create_queue_entry(video, index)
                    queue_manager.add_to_queue(server_id, entry)
                    await interaction.followup.send(f"Added to queue: {entry.title}")
                else:
                    logging.warning(f"Skipping unavailable video at index {index}")
                    await interaction.followup.send(f"Skipping unavailable video at index {index}")
            except yt_dlp.utils.ExtractorError as e:
                logging.warning(f"Skipping unavailable video at index {index}: {str(e)}")
                await interaction.followup.send(f"Skipping unavailable video at index {index}")
            except Exception as e:
                logging.error(f"Error processing video at index {index}: {str(e)}")
                await interaction.followup.send(f"Error processing video at index {index}: {str(e)}")

    await send_queue_update(interaction, server_id)

async def process_single_video_or_mp3(url, interaction):
    if url.lower().endswith('.mp3'):
        logging.debug(f"Processing MP3 file: {url}")
        print(f"Processing MP3 file: {url}")
        return QueueEntry(video_url=url, best_audio_url=url, title=url.split('/')[-1], is_playlist=False)
    else:
        video_info = await fetch_info(url)
        if video_info:
            logging.debug(f"Processing single video: {video_info.get('title', 'Unknown title')}")
            print(f"Processing single video: {video_info.get('title', 'Unknown title')}")
            return create_queue_entry(video_info, None)
        else:
            await interaction.response.send_message("Error retrieving video data.")
            logging.error("Error retrieving video data.")
            print("Error retrieving video data.")
            return None
class AudioBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        logging.debug("Initializing AudioBot")
        super().__init__(command_prefix, intents=intents)
        self.message_views = {}
        self.now_playing_messages = []

    async def setup_hook(self):
        logging.debug("Setting up hook for AudioBot")
        dummy_entry = QueueEntry(video_url='', best_audio_url='', title='dummy', is_playlist=False)
        self.add_view(ButtonView(self, dummy_entry))
        await self.tree.sync()

    async def on_ready(self):
        logging.info(f'{self.user} is now connected and ready.')
        print(f'{self.user} is now connected and ready.')

    async def on_message(self, message):
        view = self.message_views.get(message.id)
        if view:
            await message.edit(view=view)
        
        # Check for mp3_list command trigger
        if message.content.startswith(".mp3_list"):
            ctx = await self.get_context(message)
            await self.invoke(ctx)

    def add_now_playing_message(self, message_id):
        self.now_playing_messages.append(message_id)

    def clear_now_playing_messages(self):
        self.now_playing_messages.clear()


class ButtonView(discord.ui.View):
    def __init__(self, bot, entry: QueueEntry, paused: bool = False, current_user: Optional[discord.User] = None):
        logging.debug(f"Initializing ButtonView for: {entry.title}")
        super().__init__(timeout=None)
        self.bot = bot
        self.paused = paused
        self.entry = entry
        self.current_user = current_user

        # Initialize buttons with guild information if necessary
        self.pause_button = Button(label="⏸️ Pause", style=discord.ButtonStyle.primary, custom_id=f"pause-{uuid.uuid4()}")
        self.resume_button = Button(label="▶️ Resume", style=discord.ButtonStyle.primary, custom_id=f"resume-{uuid.uuid4()}")
        self.stop_button = Button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id=f"stop-{uuid.uuid4()}")
        self.skip_button = Button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id=f"skip-{uuid.uuid4()}")
        self.restart_button = Button(label="🔄 Restart", style=discord.ButtonStyle.secondary, custom_id=f"restart-{uuid.uuid4()}")
        self.shuffle_button = Button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, custom_id=f"shuffle-{uuid.uuid4()}")
        self.list_queue_button = Button(label="📜 List Queue", style=discord.ButtonStyle.secondary, custom_id=f"list_queue-{uuid.uuid4()}")
        self.remove_button = Button(label="❌ Remove", style=discord.ButtonStyle.danger, custom_id=f"remove-{uuid.uuid4()}")
        self.previous_button = Button(label="⏮️ Previous", style=discord.ButtonStyle.secondary, custom_id=f"previous-{uuid.uuid4()}")
        self.loop_button = Button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id=f"loop-{uuid.uuid4()}")
        self.move_up_button = Button(label="⬆️ Move Up", style=discord.ButtonStyle.secondary, custom_id=f"move_up-{uuid.uuid4()}")
        self.move_down_button = Button(label="⬇️ Move Down", style=discord.ButtonStyle.secondary, custom_id=f"move_down-{uuid.uuid4()}")
        self.move_to_top_button = Button(label="⬆️⬆️ Move to Top", style=discord.ButtonStyle.secondary, custom_id=f"move_to_top-{uuid.uuid4()}")
        self.move_to_bottom_button = Button(label="⬇️⬇️ Move to Bottom", style=discord.ButtonStyle.secondary, custom_id=f"move_to_bottom-{uuid.uuid4()}")

        self.favorite_button = Button(
            label="⭐ Favorite" if not self.is_favorited_by_current_user() else "💛 Favorited",
            style=discord.ButtonStyle.secondary if not self.is_favorited_by_current_user() else discord.ButtonStyle.primary,
            custom_id=f"favorite-{uuid.uuid4()}"
        )

        self.lyrics_button = Button(label="Lyrics", style=discord.ButtonStyle.secondary, custom_id=f"lyrics-{uuid.uuid4()}")

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

    async def refresh_all_views(self):
        for message_id in self.bot.now_playing_messages:
            try:
                channel = self.bot.get_channel(self.entry.guild.id)  # Assuming the channel ID is the same as the guild ID for simplicity
                message = await channel.fetch_message(message_id)
                await message.edit(view=self)
            except Exception as e:
                logging.error(f"Error refreshing view for message {message_id}: {e}")
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

        logging.debug(f"Checking guild attribute for entry: {self.entry.title}")
        print(f"Checking guild attribute for entry: {self.entry.title} with guild: {self.entry.guild}")

        if self.entry.guild:
            server_id = str(self.entry.guild.id)
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
        self.loop_button.style = discord.ButtonStyle.primary if queue_manager.loop else discord.ButtonStyle.secondary
        self.add_item(self.loop_button)

    async def refresh_view(self, interaction):
        self.update_buttons()
        await interaction.message.edit(view=self)

    async def lyrics_button_callback(self, interaction: discord.Interaction):
        logging.debug(f"Lyrics button clicked for: {self.entry.title}")
        await interaction.response.defer(ephemeral=True)

        lyrics = await get_lyrics(self.entry.title)

        if "Lyrics for " in lyrics:
            lyrics_filename = f"{self.entry.title.replace(' ', '_')}_lyrics.txt"
            with open(lyrics_filename, 'w', encoding='utf-8') as f:
                f.write(lyrics)
            file = discord.File(lyrics_filename, filename=lyrics_filename)
            await interaction.followup.send(file=file)
            os.remove(lyrics_filename)
        else:
            await interaction.followup.send(lyrics)

    async def loop_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # await interaction.response.defer()  # Defer the response to get more time
        logging.debug("Loop button callback triggered")

        if queue_manager.currently_playing:
            queue_manager.loop = not queue_manager.loop
            self.loop_button.label = "🔁 Looped" if queue_manager.loop else "🔁 Loop"
            self.loop_button.style = discord.ButtonStyle.primary if queue_manager.loop else discord.ButtonStyle.secondary
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
        await self.refresh_all_views()  # Update all instances of "Now Playing"
        await interaction.followup.send(f"{'Added to' if self.entry.is_favorited else 'Removed from'} favorites.", ephemeral=True)

    async def update_now_playing(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        favorited_by = ', '.join([user['name'] for user in self.entry.favorited_by]) if self.entry.favorited_by else "No one"
        embed.set_field_at(0, name="Favorited by", value=favorited_by, inline=False)
        await interaction.message.edit(embed=embed, view=self)

    async def pause_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Defer the response to give more time for processing
        try:
            if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
                interaction.guild.voice_client.pause()
                self.paused = True
                self.entry.pause_start_time = datetime.now()  # Record the time when paused
                await self.refresh_view(interaction)
                await interaction.followup.send('Playback paused.', ephemeral=True)
        except Exception as e:
            logging.error(f"Error in pause_button_callback: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    async def resume_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Defer the response to give more time for processing
        try:
            if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
                interaction.guild.voice_client.resume()
                self.paused = False
                paused_duration = datetime.now() - self.entry.pause_start_time  # Calculate the pause duration
                self.entry.paused_duration += paused_duration  # Adjust total paused duration
                self.entry.start_time += paused_duration  # Adjust start time by the pause duration
                await self.refresh_view(interaction)
                await interaction.followup.send('Playback resumed.', ephemeral=True)
        except Exception as e:
            logging.error(f"Error in resume_button_callback: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    async def stop_button_callback(self, interaction: discord.Interaction):
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

    async def skip_button_callback(self, interaction: discord.Interaction):
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

    async def restart_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()  # Defer the response
        if not queue_manager.currently_playing:
            await interaction.followup.send("No track is currently playing.", ephemeral=True)
            return

        current_entry = queue_manager.currently_playing
        queue_manager.is_restarting = True

        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await play_audio(interaction, current_entry)

    async def shuffle_button_callback(self, interaction: discord.Interaction):
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
        response = "Queue after shuffle:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

        max_length = 2000  # Discord message character limit
        chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

        for chunk in chunks:
            await interaction.channel.send(chunk)
        
        if first_entry_before_shuffle or any(vc.is_paused() for vc in interaction.guild.voice_clients):
            await send_now_playing(interaction, first_entry_before_shuffle)

    async def list_queue_button_callback(self, interaction: discord.Interaction):
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
                await send_now_playing(interaction, queue_manager.currently_playing)

    async def remove_button_callback(self, interaction: discord.Interaction):
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

    async def previous_button_callback(self, interaction: discord.Interaction):
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
            await play_audio(interaction, entry)
            await self.refresh_view(interaction)


    async def move_up_button_callback(self, interaction: discord.Interaction):
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

    async def move_down_button_callback(self, interaction: discord.Interaction):
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

    async def move_to_top_button_callback(self, interaction: discord.Interaction):
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

    async def move_to_bottom_button_callback(self, interaction: discord.Interaction):
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


class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.debug("Initializing MusicCommands Cog")

    @app_commands.command(name='play_next_in_queue', description='Move a specified track to the second position in the queue.')
    async def play_next(self, interaction: discord.Interaction, youtube_url: str = None, youtube_title: str = None, mp3_file: Optional[Attachment] = None):
        await interaction.response.defer()  # Defer the interaction response
        logging.debug(f"Play next command executed for youtube_url: {youtube_url}, youtube_title: {youtube_title}, mp3_file: {mp3_file}")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)

        if youtube_url:
            if "list=" in youtube_url:
                playlist_length = await fetch_playlist_length(youtube_url)
                for index in range(1, playlist_length + 1):
                    video_info = await fetch_info(youtube_url, index=index)
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
                            queue.insert(index, entry)
                            await interaction.followup.send(f"Added to queue: {entry.title} at position {index + 1}")
                            queue_manager.save_queues()
                            if not interaction.guild.voice_client.is_playing():
                                await play_audio(interaction, entry)
                    else:
                        await interaction.followup.send(f"Failed to retrieve video at index {index}")
                        break
            else:
                entry = await process_single_video_or_mp3(youtube_url, interaction)
                if entry:
                    queue.insert(1, entry)
                    await interaction.followup.send(f"'{entry.title}' added to the queue at position 2.")
                    if not interaction.guild.voice_client.is_playing():
                        await play_audio(interaction, entry)
            return

        if youtube_title:
            try:
                videos_search = VideosSearch(youtube_title, limit=1)
                search_result = videos_search.result()

                if not search_result or not search_result['result']:
                    await interaction.followup.send("No video found for the youtube_title.")
                    return

                video_info = search_result['result'][0]
                video_url = video_info['link']
                title = video_info['title']
                thumbnail = video_info['thumbnails'][0]['url']
                duration_str = video_info.get('duration', '0:00')

                duration_parts = list(map(int, duration_str.split(':')))
                if len(duration_parts) == 2:
                    duration = duration_parts[0] * 60 + duration_parts[1]
                else:
                    duration = duration_parts[0]

                ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'ignoreerrors': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.get_running_loop().run_in_executor(None, lambda: ydl.extract_info(video_url, download=False))
                    best_audio_url = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), video_url)

                entry = QueueEntry(
                    video_url=video_url,
                    best_audio_url=best_audio_url,
                    title=title,
                    is_playlist=False,
                    thumbnail=thumbnail,
                    duration=duration
                )

                queue.insert(1, entry)
                queue_manager.save_queues()
                await interaction.followup.send(f"'{entry.title}' added to the queue at position 2.")
                if not interaction.guild.voice_client.is_playing():
                    await play_audio(interaction, entry)

            except Exception as e:
                logging.error(f"Error in play_next command: {e}")
                await interaction.followup.send("An error occurred while searching for the video.")
            return

        if mp3_file:
            file_path = await download_file(mp3_file.url, 'Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s')
            if file_path:
                metadata = extract_mp3_metadata(file_path)
                entry = QueueEntry(
                    video_url=mp3_file.url,
                    best_audio_url=file_path,
                    title=metadata['title'],
                    is_playlist=False,
                    playlist_index=None,
                    thumbnail=metadata['thumbnail'],
                    duration=metadata['duration']
                )
                queue.insert(1, entry)
                queue_manager.save_queues()
                await interaction.followup.send(f"Added {entry.title} to the queue at position 2.")
                if not interaction.guild.voice_client.is_playing():
                    await play_audio(interaction, entry)
            return

        await interaction.followup.send("Please provide a valid YouTube URL, YouTube title, or attach an MP3 file.")

    @app_commands.command(name='play', description='Play a YT URL, YT Title, or MP3 file if no audio is playing or add it to the end of the queue.')
    async def play(self, interaction: discord.Interaction, youtube_url: str = None, youtube_title: str = None, mp3_file: Optional[Attachment] = None):
        await interaction.response.defer()  # Defer the interaction response

        voice_client = interaction.guild.voice_client
        if not voice_client and interaction.user.voice:
            voice_client = await interaction.user.voice.channel.connect()
        elif not voice_client:
            await interaction.followup.send("You are not connected to a voice channel.")
            return

        server_id = str(interaction.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        queue = queue_manager.get_queue(server_id)

        if mp3_file:
            file_path = await download_file(mp3_file.url, 'Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s')
            if file_path:
                metadata = extract_mp3_metadata(file_path)
                entry = QueueEntry(
                    video_url=mp3_file.url,
                    best_audio_url=file_path,
                    title=metadata['title'],
                    is_playlist=False,
                    playlist_index=None,
                    thumbnail=metadata['thumbnail'],
                    duration=metadata['duration']
                )
                queue_manager.add_to_queue(server_id, entry)
                if not interaction.guild.voice_client.is_playing():
                    await play_audio(interaction, entry)
                await interaction.followup.send(f"Added {entry.title} to the queue.")
            return

        if youtube_title:
            logging.debug(f"Search YouTube command executed for query: {youtube_title}")
            try:
                videos_search = VideosSearch(youtube_title, limit=1)
                search_result = videos_search.result()

                if not search_result or not search_result['result']:
                    await interaction.followup.send("No video found for the youtube_title.")
                    return

                video_info = search_result['result'][0]
                video_url = video_info['link']
                title = video_info['title']
                thumbnail = video_info['thumbnails'][0]['url']
                duration_str = video_info.get('duration', '0:00')

                duration_parts = list(map(int, duration_str.split(':')))
                if len(duration_parts) == 2:
                    duration = duration_parts[0] * 60 + duration_parts[1]
                else:
                    duration = duration_parts[0]

                ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'ignoreerrors': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.get_running_loop().run_in_executor(None, lambda: ydl.extract_info(video_url, download=False))
                    best_audio_url = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), video_url)

                entry = QueueEntry(
                    video_url=video_url,
                    best_audio_url=best_audio_url,
                    title=title,
                    is_playlist=False,
                    thumbnail=thumbnail,
                    duration=duration
                )

                if not queue_manager.currently_playing:
                    queue.insert(0, entry)
                    queue_manager.save_queues()
                    if not interaction.guild.voice_client:
                        if interaction.user.voice:
                            await interaction.user.voice.channel.connect()
                        else:
                            await interaction.followup.send("You are not connected to a voice channel.")
                            return
                    await play_audio(interaction, entry)
                else:
                    queue_manager.add_to_queue(server_id, entry)

                await interaction.followup.send(f"Added to queue: {title}")

            except Exception as e:
                logging.error(f"Error in search_youtube command: {e}")
                await interaction.followup.send("An error occurred while searching for the video.")
            return

        if youtube_url:
            if "list=" in youtube_url:
                await process_play_command(interaction, youtube_url)
            else:
                entry = await process_single_video_or_mp3(youtube_url, interaction)
                if entry:
                    if not queue_manager.currently_playing:
                        queue.insert(0, entry)
                        await play_audio(interaction, entry)
                    else:
                        queue_manager.add_to_queue(server_id, entry)
                    await interaction.followup.send(f"Added '{entry.title}' to the queue.")
            return

        await interaction.followup.send("Please provide a valid URL, YouTube video title, or attach an MP3 file.")

    @app_commands.command(name='previous', description='Play the last entry that was being played.')
    async def previous(self, interaction: discord.Interaction):
        logging.debug("Previous command executed")
        server_id = str(interaction.guild.id)
        last_played = queue_manager.last_played_audio.get(server_id)
        if not last_played:
            await interaction.response.send_message("There was nothing played prior.")
            return

        queue = queue_manager.get_queue(server_id)
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

        **/clear_queue**
        - Clears the queue for today except the currently playing entry.

        **/list_queue**
        - Lists all entries currently in the queue.
        - Displays the current queue with each track's title and position.

        **/move_to_next [title]**
        - Moves a specified track to the second position in the queue by title.
        - If a title is provided and found in the queue, it will be moved to the second position.

        **/pause**
        - Pauses the currently playing track.

        **/play [URL or attachment]**
        - Plays audio from a YouTube URL, a YouTube title, or an attached MP3 file.
        - If a URL is provided, it can be a single video or a playlist. If it's a playlist, all videos will be added to the queue.
        - If a YouTube title is provided, the bot will search for the video and play the first result.
        - If an MP3 file is attached, it will be added to the queue and played if nothing is currently playing.

        **/play_next_in_queue [URL, YouTube title, or MP3 attachment]**
        - Adds a new entry to the second position in the queue.
        - If a URL is provided, the video or playlist will be added to the second position.
        - If a YouTube title is provided, the bot will search for the video and add the first result to the second position.
        - If an MP3 file is attached, it will be added to the second position in the queue.

        **/play_queue**
        - Starts playing the queue from the first track.

        **/previous**
        - Plays the last entry that was being played.

        **/remove_by_title [title]**
        - Removes a specific track by its title from the queue.
        - If the title is found in the queue, it will be removed.

        **/remove_queue [index]**
        - Removes a track from the queue by its index.
        - The index is the position in the queue, starting from 1.

        **/restart**
        - Restarts the currently playing track from the beginning.

        **/resume**
        - Resumes playback if it is paused.

        **/search_and_play_from_queue [title]**
        - Searches the current queue and plays the specified track.
        - Use this command to play a specific track from the queue immediately.

        **/shuffle**
        - Randomly shuffles the current queue and shows the new order.

        **/skip**
        - Skips the current track and plays the next one in the queue.
        - If there is no next track, the playback stops.

        **/stop**
        - Stops playback and disconnects the bot from the voice channel.

        **Buttons:**

        **💛 Favorited / ⭐ Favorite**
        - Toggles the favorite status of the current track.
        - Users can mark tracks as favorites, which will be displayed in the "Now Playing" embed.

        **⬇️ Move Down**
        - Moves the current track down one position in the queue.

        **⬇️⬇️ Move to Bottom**
        - Moves the current track to the bottom of the queue.

        **⬆️ Move Up**
        - Moves the current track up one position in the queue.

        **⬆️⬆️ Move to Top**
        - Moves the current track to the top of the queue.

        **📜 List Queue**
        - Lists all entries currently in the queue.
        - Displays the current queue with each track's title and position.

        **Lyrics**
        - Fetches and displays the lyrics for the current track.
        - The bot will search for the lyrics based on the current track's title and artist.

        **🔁 Loop**
        - Toggles looping of the current track.
        - If enabled, the current track will repeat after it finishes playing.
        - Continues looping the current track until the loop button is clicked again.

        **⏸️ Pause**
        - Pauses the currently playing track.

        **⏮️ Previous**
        - Plays the last entry that was being played.
        - Useful for returning to the previously played track.

        **🔄 Restart**
        - Restarts the currently playing track from the beginning.

        **⏭️ Skip**
        - Skips the current track and plays the next one in the queue.

        **⏹️ Stop**
        - Stops playback and disconnects the bot from the voice channel.

        **🔀 Shuffle**
        - Randomly shuffles the current queue and shows the new order.

        **❌ Remove**
        - Removes the current track from the queue.
        - If the removed track is currently playing, playback stops.

        **Type a command to execute it. For example: `/play https://youtube.com/watch?v=example`**

        **Always taking suggestions for the live service of Radio-Bot**
        """
        max_length = 2000
        pattern = re.compile(r"(\*\*.+?\*\*[\s\S]*?(?=\n\s*\*\*|$))")

        matches = pattern.findall(help_text)
        chunks = []
        current_chunk = ""

        for match in matches:
            if len(current_chunk) + len(match) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += match + "\n"
        
        if current_chunk:
            chunks.append(current_chunk)

        # Ensure "Buttons:" title is within the same message as the first button title and its description
        for i, chunk in enumerate(chunks):
            if "**Buttons:**" in chunk:
                button_section_start_index = chunk.index("**Buttons:**")
                before_buttons = chunk[:button_section_start_index]
                buttons_and_after = chunk[button_section_start_index:]
                if len(before_buttons) + len(buttons_and_after.split("\n", 2)[0]) > max_length:
                    chunks[i] = before_buttons
                    chunks.insert(i + 1, buttons_and_after)
                else:
                    chunks[i] = before_buttons + buttons_and_after
                break

        # Send the chunks ensuring the interaction is not responded to multiple times incorrectly
        first_message_sent = False
        for chunk in chunks:
            if not first_message_sent:
                await interaction.response.send_message(chunk)
                first_message_sent = True
            else:
                await interaction.followup.send(chunk)
    

    @app_commands.command(name='remove_by_title', description='Remove a track from the queue by title.')
    async def remove_by_title(self, interaction: discord.Interaction, title: str):
        logging.debug(f"Remove by title command executed for title: {title}")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return

        original_length = len(queue)
        queue = [entry for entry in queue if entry.title != title]
        if len(queue) == original_length:
            await interaction.response.send_message(f"No track found with title '{title}'.")
        else:
            queue_manager.queues[server_id] = queue
            queue_manager.save_queues()
            await interaction.response.send_message(f"Removed '{title}' from the queue.")

    @app_commands.command(name='shuffle', description='Shuffle the current queue.')
    async def shuffle(self, interaction: discord.Interaction):
        logging.debug("Shuffle command executed")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return
        first_entry_before_shuffle = queue_manager.currently_playing

        queue_manager.has_been_shuffled = True
        random.shuffle(queue)
        for entry in queue:
            entry.has_been_arranged = False
        queue_manager.queues[server_id] = queue
        queue_manager.save_queues()

        titles = [entry.title for entry in queue]
        response = "Queue after shuffle:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

        max_length = 2000  # Discord message character limit
        chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

        for chunk in chunks:
            await interaction.channel.send(chunk)
        
        if first_entry_before_shuffle or any(vc.is_paused() for vc in interaction.guild.voice_clients):
            await send_now_playing(interaction, first_entry_before_shuffle)

    @app_commands.command(name='play_queue', description='Play the current queue.')
    async def play_queue(self, interaction: discord.Interaction):
        logging.debug("Play queue command executed")
        
        await interaction.response.defer()  # Defer the response to give more time for processing

        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.followup.send("Queue is empty, please add some tracks first.")
            return

        entry = queue[0] if queue else None
        if entry:
            if not interaction.guild.voice_client:
                if interaction.user.voice:
                    await interaction.user.voice.channel.connect()
                else:
                    await interaction.followup.send("You are not connected to a voice channel.")
                    return

            await play_audio(interaction, entry)
        else:
            await interaction.followup.send("Queue is empty.")

    @app_commands.command(name='list_queue', description='List all entries in the current queue.')
    async def list_queue(self, interaction: discord.Interaction):
        logging.debug("List queue command executed")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
        else:
            titles = [entry.title for entry in queue]
            response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

            max_length = 2000  # Discord message character limit
            chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

            for chunk in chunks:
                await interaction.channel.send(chunk)
            
            if queue_manager.currently_playing or any(vc.is_paused() for vc in interaction.guild.voice_clients):
                await send_now_playing(interaction, queue_manager.currently_playing)

    @app_commands.command(name='remove_queue', description='Remove a track from the queue by index.')
    async def remove_queue(self, interaction: discord.Interaction, index: int):
        logging.debug(f"Remove queue command executed for index: {index}")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
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
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.response.send_message("Queue is empty.")
            return

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            current_entry = queue_manager.currently_playing
            if current_entry:
                if current_entry.has_been_arranged and current_entry.has_been_played_after_arranged:
                    current_entry.has_been_arranged = False
                    current_entry.has_been_played_after_arranged = False
                elif current_entry.has_been_arranged and not current_entry.has_been_played_after_arranged:
                    current_entry.has_been_played_after_arranged = True
                    queue.remove(current_entry)
                    queue.append(current_entry)
                    queue_manager.save_queues()
                elif not queue_manager.has_been_shuffled:
                    queue.remove(current_entry)
                    queue.append(current_entry)
                    queue_manager.save_queues()
                interaction.guild.voice_client.stop()
                await asyncio.sleep(0.5)

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
        queue_manager.currently_playing = None
        queue_manager.stop_is_triggered = True
        if interaction.guild.voice_client:
            try:
                interaction.guild.voice_client.stop()
            except Exception as e:
                logging.error(f"Error stopping the voice client: {e}")
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message('Playback stopped and disconnected.', ephemeral=True)

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
            
    @commands.command(name='mp3_list_next')
    async def mp3_list_next(self, ctx):
        logging.debug("mp3_list_next command invoked")
        print("mp3_list_next command invoked")

        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not voice_client and ctx.author.voice:
            logging.debug("Connecting to voice channel")
            print("Connecting to voice channel")
            voice_client = await ctx.author.voice.channel.connect()
        elif not voice_client:
            logging.warning("User is not connected to a voice channel")
            print("User is not connected to a voice channel")
            await ctx.send("You are not connected to a voice channel.")
            return

        server_id = str(ctx.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        logging.debug(f"Queue exists ensured for server {server_id}")
        print(f"Queue exists ensured for server {server_id}")

        if ctx.message.attachments:
            logging.debug("Processing attachments")
            print("Processing attachments")
            current_index = 1
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith('.mp3'):
                    logging.info(f"Downloading attachment: {attachment.filename}")
                    print(f"Downloading attachment: {attachment.filename}")
                    file_path = await download_file(attachment.url, 'Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s')
                    if file_path:
                        metadata = extract_mp3_metadata(file_path)
                        entry = QueueEntry(
                            video_url=attachment.url,
                            best_audio_url=file_path,
                            title=metadata['title'],
                            is_playlist=False,
                            playlist_index=None,
                            thumbnail=metadata['thumbnail'],
                            duration=metadata['duration']
                        )
                        queue = queue_manager.get_queue(server_id)
                        queue.insert(current_index, entry)
                        current_index += 1
                        queue_manager.save_queues()
                        logging.info(f"Added '{entry.title}' to queue at position {current_index}")
                        print(f"Added '{entry.title}' to queue at position {current_index}")
                        await ctx.send(f"'{entry.title}' added to the queue at position {current_index}.")
                        if not voice_client.is_playing() and current_index == 2:
                            await play_audio(ctx, entry)
            return
        else:
            logging.warning("No valid URL or attachment provided")
            print("No valid URL or attachment provided")
            await ctx.send("Please provide a valid URL or attach an MP3 file.")

    @commands.command(name='mp3_list')
    async def mp3_list(self, ctx, url: str = None):
        logging.debug("mp3_list command invoked")
        print("mp3_list command invoked")

        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not voice_client and ctx.author.voice:
            logging.debug("Connecting to voice channel")
            print("Connecting to voice channel")
            voice_client = await ctx.author.voice.channel.connect()
        elif not voice_client:
            logging.warning("User is not connected to a voice channel")
            print("User is not connected to a voice channel")
            await ctx.send("You are not connected to a voice channel.")
            return

        server_id = str(ctx.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        logging.debug(f"Queue exists ensured for server {server_id}")
        print(f"Queue exists ensured for server {server_id}")

        if ctx.message.attachments:
            logging.debug("Processing attachments")
            print("Processing attachments")
            first_entry_processed = False
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith('.mp3'):
                    logging.info(f"Downloading attachment: {attachment.filename}")
                    print(f"Downloading attachment: {attachment.filename}")
                    file_path = await download_file(attachment.url, 'Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s')
                    if file_path:
                        metadata = extract_mp3_metadata(file_path)
                        entry = QueueEntry(
                            video_url=attachment.url,
                            best_audio_url=file_path,
                            title=metadata['title'],
                            is_playlist=False,
                            playlist_index=None,
                            thumbnail=metadata['thumbnail'],
                            duration=metadata['duration']
                        )
                        queue_manager.add_to_queue(server_id, entry)
                        logging.info(f"Added '{entry.title}' to queue")
                        print(f"Added '{entry.title}' to queue")
                        await ctx.send(f"'{entry.title}' added to the queue.")
                        if not voice_client.is_playing() and not first_entry_processed:
                            await play_audio(ctx, entry)
                            first_entry_processed = True
            return
        else:
            logging.warning("No valid URL or attachment provided")
            print("No valid URL or attachment provided")
            await ctx.send("Please provide a valid URL or attach an MP3 file.")


    @app_commands.autocomplete(title="title_autocomplete")
    async def title_autocomplete(self, interaction: discord.Interaction, current: str):
        server_id = str(interaction.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        queue = queue_manager.get_queue(server_id)
        titles = [entry.title for entry in queue if current.lower() in entry.title.lower()]
        return [app_commands.Choice(name=title, value=title) for title in titles[:25]]

    @app_commands.command(name="search_and_play_from_queue", description="Search the current queue and play the specified track.")
    @app_commands.autocomplete(title=title_autocomplete)
    async def search_and_play_from_queue(self, interaction: discord.Interaction, title: str):
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)

        entry_index = next((i for i, entry in enumerate(queue) if entry.title == title), None)
        if entry_index is None:
            await interaction.response.send_message("No match found in the current queue.")
            return

        entry = queue.pop(entry_index)
        queue.insert(0, entry)
        queue_manager.save_queues()

        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await asyncio.sleep(1)

        if not voice_client:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()

        await play_audio(interaction, entry)

    @app_commands.command(name='move_to_next', description="Move the specified track in the queue to the second position.")
    @app_commands.autocomplete(title=title_autocomplete)
    async def queue_up_next(self, interaction: discord.Interaction, title: str):
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)

        entry_index = next((i for i, entry in enumerate(queue) if entry.title == title), None)
        if entry_index is None:
            await interaction.response.send_message("No match found in the current queue.")
            return

        entry = queue.pop(entry_index)
        queue.insert(1, entry)
        queue_manager.save_queues()
        
        await interaction.response.send_message(f"Moved '{title}' to the second position in the queue.")
    
    @app_commands.command(name='clear_queue', description='Clear the queue except the currently playing entry.')
    async def clear_queue(self, interaction: discord.Interaction):
        logging.debug("Clear queue command executed")
        server_id = str(interaction.guild.id)
        current_entry = queue_manager.currently_playing
        if server_id in queue_manager.queues:
            if current_entry and current_entry in queue_manager.queues[server_id]:
                queue_manager.queues[server_id] = [current_entry]
            else:
                queue_manager.queues[server_id] = []
            queue_manager.save_queues()
            await interaction.response.send_message(f"The queue for server '{interaction.guild.name}' has been cleared, except the currently playing entry.")
        else:
            await interaction.response.send_message(f"There is no queue for server '{interaction.guild.name}' to clear.")

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

if __name__ == '__main__':
    run_bot()