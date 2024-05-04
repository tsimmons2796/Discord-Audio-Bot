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

async def fetch_info(url, start_index=None):
    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': False, 'playlist_items': f'{start_index}-{start_index+9}', 'ignoreerrors': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))

async def fetch_playlist_length(url):
    ydl_opts = {'quiet': True, 'noplaylist': False, 'extract_entries': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
        return len(info.get('entries', []))

async def process_play_command(ctx, url):
    playlist_length = await fetch_playlist_length(url)
    logging.info(f"Playlist length: {playlist_length}")
    print(f"Playlist length: {playlist_length}")
    
    index = 1
    while index <= playlist_length:
        logging.info(f"Processing index: {index}")
        print(f"Processing index: {index}")
        
        info = await fetch_info(url, start_index=index)
        entries = info['entries'] if 'entries' in info else [info]
        
        if not entries:
            logging.info("No entries retrieved.")
            print("No entries retrieved.")
            break
        
        video = entries[0]  # We'll just consider the first video from the response
        
        # Queue up the video with available information
        entry = QueueEntry(video.get('webpage_url', ''), '', video.get('title', 'Unknown title'), True, index)
        queue_manager.add_to_queue(entry)
        await ctx.send(f'Added to queue: {entry.title}')
        logging.info(f'Added to queue: {entry.title}')
        print(f'Added to queue: {entry.title}')
        
        # Fetch additional data (such as URL) for the video
        audio_url = next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), None)
        if audio_url:
            entry.best_audio_url = audio_url
            await ctx.send(f'URL found for {entry.title}')
            logging.info(f'URL found for {entry.title}')
            print(f'URL found for {entry.title}')
        else:
            await ctx.send(f'URL not found for {entry.title}')
            logging.info(f'URL not found for {entry.title}')
            print(f'URL not found for {entry.title}')
        
        # Start playing audio immediately for the first video
        if index == 1:
            await play_audio(ctx, entry)
        
        index += 1

async def play_audio(ctx, entry):
    if not ctx.voice_client.is_playing():
        ctx.voice_client.play(discord.FFmpegPCMAudio(entry.best_audio_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop))
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
        ydl_opts = {
            'quiet': True,
            'force_generic_extractor': True,
            'playlist_items': '3',
            'extract_audio': True,
            'audio_format': 'mp3',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(playlist_url, download=False)
            print(info_dict)
            if 'entries' in info_dict:
                video_info = info_dict['entries'][2]
                title = video_info.get('title', 'Title not available')
                url = video_info.get('url')
                if url:
                    await ctx.send(f"Title: {title}\nURL: {url}")
                else:
                    await ctx.send("URL not available for the video at index 3.")
            else:
                await ctx.send("Invalid playlist URL or video not found at index 3.")

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
