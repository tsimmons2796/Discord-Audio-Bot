import json
from datetime import datetime
import logging
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp
from typing import List, Dict, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import random
import aiohttp
import re

# Configure logging
logging.basicConfig(level=logging.INFO, filename='queue_log.log', format='%(asctime)s:%(levelname)s:%(message)s')

class QueueEntry:
    def __init__(self, video_url: str, best_audio_url: str, title: str, is_playlist: bool, playlist_index: Optional[int] = None):
        self.video_url = video_url
        self.best_audio_url = best_audio_url
        self.title = title
        self.is_playlist = is_playlist
        self.playlist_index = playlist_index

    def to_dict(self):
        return {
            'video_url': self.video_url,
            'best_audio_url': self.best_audio_url,
            'title': self.title,
            'is_playlist': self.is_playlist,
            'playlist_index': self.playlist_index
        }

class BotQueue:
    def __init__(self):
        self.currently_playing = None
        self.queues = self.load_queues()
        self.ensure_today_queue_exists()
        self.last_played_audio = self.load_last_played_audio()
        self.is_restarting = False  # Flag to track if restart command is triggered
        self.hasBeenShuffled = False

    def load_queues(self) -> Dict[str, List[QueueEntry]]:
        try:
            with open('queues.json', 'r') as file:
                queues_data = json.load(file)
            return {date: [QueueEntry(**entry) for entry in entries] for date, entries in queues_data.items()}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Failed to load queues: {e}")
            return {}

    def load_last_played_audio(self) -> str:
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
        return await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))

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

async def play_audio(ctx, entry):
    queue_manager.currently_playing = entry
    queue_manager.save_queues()

    logging.info(f"Starting playback for: {entry.title} (URL: {entry.best_audio_url})")
    logging.info(f"Buffer size set to: 65536k")

    def after_playing(error):
        if error:
            logging.error(f"Error playing {entry.title}: {error}")
            asyncio.run_coroutine_threadsafe(ctx.send("Error occurred during playback."), ctx.bot.loop).result()
        else:
            logging.info(f"Finished playing {entry.title} at {datetime.now()}")
            if not queue_manager.is_restarting:
                queue_manager.last_played_audio = entry.title
            queue_manager.save_queues()
            asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop).result()

    async def start_playback():
        try:
            # Log the state of the voice client before starting playback
            if ctx.voice_client is None:
                logging.warning("Voice client is None. Attempting to connect.")
            elif not ctx.voice_client.is_connected():
                logging.warning("Voice client is not connected. Attempting to reconnect.")
            elif ctx.voice_client.is_playing():
                logging.warning("Voice client is already playing.")
            elif ctx.voice_client.is_paused():
                logging.warning("Voice client is paused.")

            # Determine if the audio source is a local file or a URL
            audio_source = discord.FFmpegPCMAudio(
                entry.best_audio_url if not entry.best_audio_url.startswith('Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s') else entry.best_audio_url,
                options='-bufsize 65536k -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -vn'
            )
            if not ctx.voice_client.is_playing():
                ctx.voice_client.play(audio_source, after=after_playing)
                await ctx.send(f'Now playing: {entry.title}')
                logging.info(f"Playback started for {entry.title} at {datetime.now()}")
        except Exception as e:
            logging.error(f"Exception during playback: {e}")
            await ctx.send(f"An error occurred during playback: {e}")

    await start_playback()

async def play_next(ctx):
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
            await play_audio(ctx, entry)

async def process_play_command(ctx, url):
    first_video_info = await fetch_info(url, index=1)
    if not first_video_info or 'entries' not in first_video_info or not first_video_info['entries']:
        await ctx.send("Could not retrieve the first video of the playlist.")
        return

    first_video = first_video_info['entries'][0]
    if first_video:
        first_entry = QueueEntry(
            video_url=first_video.get('webpage_url', ''),
            best_audio_url=next((f['url'] for f in first_video['formats'] if f.get('acodec') != 'none'), ''),
            title=first_video.get('title', 'Unknown title'),
            is_playlist=True,
            playlist_index=1
        )
        queue_manager.add_to_queue(first_entry)
        await ctx.send(f"Added to queue: {first_entry.title}")
        await play_audio(ctx, first_entry)
    else:
        await ctx.send("No video found at the specified index.")
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
                    playlist_index=index
                )
                queue_manager.add_to_queue(entry)
                await ctx.send(f"Added to queue: {entry.title}")
            else:
                await ctx.send(f"Failed to retrieve video at index {index}")

    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    titles = [entry.title for entry in queue]
    response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
    await ctx.send(response)

async def process_single_video_or_mp3(url, ctx):
    if url.lower().endswith('.mp3'):
        return QueueEntry(video_url=url, best_audio_url=url, title=url.split('/')[-1], is_playlist=False)
    else:
        video_info = await fetch_info(url)
        if video_info:
            return QueueEntry(
                video_url=video_info.get('webpage_url', url),
                best_audio_url=next((f['url'] for f in video_info['formats'] if f.get('acodec') != 'none'), url),
                title=video_info.get('title', 'Unknown title'),
                is_playlist=False
            )
        else:
            await ctx.send("Error retrieving video data.")
            return None

async def handle_playlist(ctx, entries):
    for index, video in enumerate(entries, start=1):
        entry = QueueEntry(
            video_url=video.get('webpage_url', ''),
            best_audio_url=next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), ''),
            title=video.get('title', 'Unknown title'),
            is_playlist=True,
            playlist_index=index
        )
        queue_manager.add_to_queue(entry)
        if index == 1:
            await play_audio(ctx, entry)

async def handle_single_video(ctx, info):
    entry = QueueEntry(
        video_url=info.get('webpage_url', ''),
        best_audio_url=next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), ''),
        title=info.get('title', 'Unknown title'),
        is_playlist=False
    )
    queue_manager.add_to_queue(entry)
    await play_audio(ctx, entry)

def setup_commands(bot):
    @bot.command(name='previous')
    async def previous(ctx):
        last_played = queue_manager.last_played_audio
        print(f'last_played_audio: {last_played.title}')
        if not last_played:
            await ctx.send("There was nothing played prior.")
            return

        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        entry = next((e for e in queue if e.title == last_played), None)

        if not entry:
            await ctx.send("No previously played track found.")
            return

        queue.remove(entry)
        queue.insert(1, entry)
        queue_manager.save_queues()
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await asyncio.sleep(0.5)

    bot.remove_command('help')

    @bot.command(name='help')
    async def help_command(ctx):
        help_text = """
    Here are the commands you can use:

    **.play [URL or attachment]** - Play audio from a YouTube URL or attached MP3 file.
    **.play_video [title]** - Plays the video by title from the queue.
    **.shuffle** - Randomly shuffles the queue and shows the new order.
    **.list_queue** - Lists all entries currently in the queue.
    **.play_queue** - Starts playing the queue from the first track.
    **.remove [title]** - Removes a specific track by title from the queue.
    **.skip** - Skips the current track and plays the next one in the queue.
    **.pause** - Pauses the currently playing track.
    **.resume** - Resumes playback if it's paused.
    **.stop** - Stops playback and disconnects the bot from the voice channel.
    **.previous** - Plays the last entry that was being played.
    **.restart** - Restarts the currently playing track from the beginning.
    
    **Always taking suggestions for the live service of Radio-Bot**

    Type a command to execute it. For example: `.play https://youtube.com/watch?v=example`
    """
        await ctx.send(help_text)

    @bot.command(name='play_video')
    async def play_video(ctx, *, title: str):
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        
        entry_index = next((i for i, entry in enumerate(queue) if entry.title == title), None)
        if entry_index is None:
            await ctx.send(f"No video found with title '{title}'.")
            return

        entry = queue.pop(entry_index)
        
        if ctx.voice_client:
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                if 'Discord-Audio-Bot\\Discord-Audio-Bot\\downloaded-mp3s' in entry.best_audio_url:
                    logging.info(f'Moving {entry.title} to the front of the queue.')
                    queue.insert(0, entry)
                    ctx.voice_client.stop()
                else:
                    logging.info(f'Moving {entry.title} to second in position.')
                    queue.insert(1, entry)
                ctx.voice_client.stop()
                await asyncio.sleep(1)

        if not ctx.voice_client:
            if ctx.author.voice:
                queue.insert(0, entry)
                await ctx.author.voice.channel.connect()
                await play_audio(ctx, entry)
            else:
                await ctx.send("You are not connected to a voice channel.")
                return


    @bot.command(name='remove')
    async def remove(ctx, *, title: str):
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await ctx.send("The queue is currently empty.")
            return
        
        original_length = len(queue)
        queue = [entry for entry in queue if entry.title != title]
        if len(queue) == original_length:
            await ctx.send(f"No track found with title '{title}'.")
        else:
            queue_manager.queues[today_str] = queue
            queue_manager.save_queues()
            await ctx.send(f"Removed '{title}' from the queue.")

    @bot.command(name='shuffle')
    async def shuffle(ctx):
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await ctx.send("The queue is currently empty.")
            return
        
        random.shuffle(queue)
        queue_manager.hasBeenShuffled = True
        queue_manager.queues[today_str] = queue
        queue_manager.save_queues()

        titles = [entry.title for entry in queue]
        response = "Queue after shuffle:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
        await ctx.send(response)

    @bot.command(name='play_queue')
    async def play_queue(ctx):
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await ctx.send("Queue is empty, please add some tracks first.")
            return

        entry = queue[0] if queue else None
        if entry:
            if not ctx.voice_client:
                if ctx.author.voice:
                    await ctx.author.voice.channel.connect()
                else:
                    await ctx.send("You are not connected to a voice channel.")
                    return

            await play_audio(ctx, entry)
        else:
            await ctx.send("Queue is empty.")

    @bot.command(name='play')
    async def play(ctx, url: str = None):
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

    @bot.command(name='list_queue')
    async def list_queue(ctx):
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
        if not queue:
            await ctx.send("The queue is currently empty.")
        else:
            titles = [entry.title for entry in queue]
            response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
            
            max_length = 2000
            chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]
            
            for chunk in chunks:
                await ctx.send(chunk)

    @bot.command(name='remove_queue')
    async def remove_queue(ctx, index: int):
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
        if 0 <= index < len(queue):
            removed_entry = queue.pop(index)
            queue_manager.save_queues()
            await ctx.send(f"Removed '{removed_entry.title}' from the queue.")
        else:
            await ctx.send("Invalid index. Please provide a valid index of the song to remove.")

    @bot.command(name='skip')
    async def skip(ctx):
        date_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(date_str)
        if not queue:
            await ctx.send("Queue is empty.")
            return

        if ctx.voice_client and ctx.voice_client.is_playing():
            current_entry = queue_manager.currently_playing
            if current_entry and not queue_manager.hasBeenShuffled:
                queue.remove(current_entry)
                queue.append(current_entry)
                queue_manager.save_queues()
            
            queue_manager.hasBeenShuffled = False
            ctx.voice_client.stop()
            await asyncio.sleep(0.5)

    @bot.command(name='pause')
    async def pause(ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send('Playback paused.')
            logging.info("Playback paused.")
            print("Playback paused.")

    @bot.command(name='resume')
    async def resume(ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Playback resumed.')
            logging.info("Playback resumed.")
            print("Playback resumed.")

    @bot.command(name='stop')
    async def stop(ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            await ctx.send('Playback stopped and disconnected.')
            logging.info("Playback stopped and bot disconnected.")
            print("Playback stopped and bot disconnected.")

    @bot.command(name='restart')
    async def restart(ctx):
        if not queue_manager.currently_playing:
            await ctx.send("No track is currently playing.")
            return

        current_entry = queue_manager.currently_playing
        queue_manager.is_restarting = True

        if ctx.voice_client:
            ctx.voice_client.stop()
            await asyncio.sleep(0.5)

        # await play_audio(ctx, current_entry)

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=".", intents=intents)

    @client.event
    async def on_ready():
        logging.info(f'{client.user} is now connected and ready.')
        print(f'{client.user} is now connected and ready.')
        # Optionally, start playing the queue on bot startup:
        # await play_queue(client)

    setup_commands(client)
    client.run(TOKEN)

if __name__ == '__main__':
    run_bot()
