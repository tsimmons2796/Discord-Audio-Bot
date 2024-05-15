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
        self.queues = self.load_queues()
        self.ensure_today_queue_exists()

    def load_queues(self) -> Dict[str, List[QueueEntry]]:
        try:
            with open('queues.json', 'r') as file:
                data = json.load(file)
                return {k: [QueueEntry(**d) for d in v] for k, v in data.items()}
        except Exception as e:
            logging.error(f"Failed to load queues: {e}")
            return {}

    def save_queues(self):
        try:
            with open('queues.json', 'w') as file:
                json.dump({k: [entry.to_dict() for entry in v] for k, v in self.queues.items()}, file, indent=4)
        except Exception as e:
            logging.error(f"Failed to save queues: {e}")

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
    # Configuration for extracting a specific video at a given index
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': False,  # Ensure the playlist is processed
        'playlist_items': f'{index}',  # Specify the exact video by index
        'ignoreerrors': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Use a lambda to call extract_info within an executor for async operation
        return await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))

async def fetch_playlist_length(url):
    ydl_opts = {'quiet': True, 'noplaylist': False, 'extract_entries': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
        return len(info.get('entries', []))

async def process_play_command(ctx, url):
    # Retrieve playlist information with only the first video details first.
    first_video_info = await fetch_info(url, index=1)
    if not first_video_info or 'entries' not in first_video_info or not first_video_info['entries']:
        await ctx.send("Could not retrieve the first video of the playlist.")
        return

    first_video = first_video_info['entries'][0]  # Assuming we have the video
    if first_video:
        first_entry = QueueEntry(
            video_url=first_video.get('webpage_url', ''),
            best_audio_url=next((f['url'] for f in first_video['formats'] if f.get('acodec') != 'none'), ''),
            title=first_video.get('title', 'Unknown title'),
            is_playlist=True,
            playlist_index=1
        )
        queue_manager.add_to_queue(first_entry)
        await play_audio(ctx, first_entry)
    else:
        await ctx.send("No video found at the specified index.")

    # Fetch the full playlist length for further processing
    playlist_length = await fetch_playlist_length(url)
    if playlist_length > 1:
        # Process remaining videos in batches of three
        for start_index in range(2, playlist_length + 1, 3):
            end_index = min(start_index + 2, playlist_length)  # Ensure we do not go out of bounds
            for index in range(start_index, end_index + 1):
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
                    logging.info(f'Queued {entry.title} at index {index}.')
                else:
                    logging.warning(f"No video found or failed to retrieve video at index {index}.")

# async def play_audio(ctx, entry):
#     if not ctx.voice_client.is_playing():
#         ctx.voice_client.play(discord.FFmpegPCMAudio(entry.best_audio_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop))
#         await ctx.send(f'Now playing: {entry.title}')
#         logging.info(f'Now playing: {entry.title}')
#         print(f'Now playing: {entry.title}')

async def play_audio(ctx, entry):
    def after_playing(error):
        if error:
            logging.error(f"Error playing {entry.title}: {error}")
            asyncio.run_coroutine_threadsafe(ctx.send("Error occurred during playback."), ctx.bot.loop).result()
        else:
            logging.info(f"Finished playing {entry.title}.")
            asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop).result()

    if not ctx.voice_client.is_playing():
        ctx.voice_client.play(discord.FFmpegPCMAudio(entry.best_audio_url), after=after_playing)
        await ctx.send(f'Now playing: {entry.title}')
        logging.info(f'Now playing: {entry.title}')
        print(f'Now playing: {entry.title}')

async def play_next(ctx):
    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    if queue:
        entry = queue.pop(0)
        queue_manager.save_queues()
        await play_audio(ctx, entry)
    else:
        queue_manager.ensure_today_queue_exists()
        await ctx.send('Queue is empty, please add more items.')
        logging.info('Queue is empty, please add more items.')
        print('Queue is empty, please add more items.')

def setup_commands(bot):
    @bot.command(name='test')
    async def test(ctx, playlist_url):
        # Setup yt-dlp options for lazy playlist processing
        ydl_opts = {
            'quiet': True,
            'force_generic_extractor': True,
            'extract_audio': True,
            'audio_format': 'mp3',
            'lazy_playlist': True,  # Corresponds to the --lazy-playlist option
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(playlist_url, download=False)
            print(f"Extracted playlist information: {info_dict}")
            if 'entries' in info_dict:
                for index, video_info in enumerate(info_dict['entries']):
                    title = video_info.get('title', 'Title not available')
                    url = video_info.get('url', 'URL not available')
                    await ctx.send(f"Index: {index+1}, Title: {title}, URL: {url}")
                    print(f"Index: {index+1}, Title: {title}, URL: {url}")
                    if index >= 2:  # Stop after processing three entries
                        break
            else:
                await ctx.send("Invalid playlist URL or video not found.")
                print("Invalid playlist URL or video not found.")

    @bot.command(name='play_specific')
    async def play_specific(ctx, url: str, index: int):
        """
        Plays a specific video from a YouTube playlist at the given index.
        :param ctx: The context under which the command is being invoked.
        :param url: The YouTube playlist URL.
        :param index: The index of the video in the playlist to play.
        """
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                return

        info = await fetch_info(url, index=index)
        if not info or 'entries' not in info or not info['entries']:
            await ctx.send(f"Could not retrieve video at index {index}.")
            return

        video = info['entries'][0]  # Assuming we have the video
        if video:
            entry = QueueEntry(
                video_url=video.get('webpage_url', ''),
                best_audio_url=next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), ''),
                title=video.get('title', 'Unknown title'),
                is_playlist=True,
                playlist_index=index
            )
            queue_manager.add_to_queue(entry)
            await play_audio(ctx, entry)
        else:
            await ctx.send("No video found at the specified index.")

    @bot.command(name='play')
    async def play(ctx, url: str):
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                return
        await process_play_command(ctx, url)

    @bot.command(name='play-queue')
    async def play_queue(ctx):
        await ctx.send('Queue Load Started')
        await play_next(ctx)

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
