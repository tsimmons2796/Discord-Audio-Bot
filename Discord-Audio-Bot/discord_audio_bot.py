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
    def __init__(self, video_url: str, title: str, is_playlist: bool, playlist_index: Optional[int] = None):
        self.video_url = video_url
        self.title = title
        self.is_playlist = is_playlist
        self.playlist_index = playlist_index

    def to_dict(self):
        return {
            'video_url': self.video_url,
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

async def fetch_info(url):
    with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'noplaylist': False}) as ydl:
        return await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))

def setup_commands(bot):
    @bot.command(name='play')
    async def play(ctx, url: str):
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                return
        
        info = await fetch_info(url)
        entries = info['entries'] if 'entries' in info else [info]
        queue_was_empty = not bool(queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d')))
        
        for video in entries:
            audio_url = next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), None)
            if audio_url:
                entry = QueueEntry(audio_url, video.get('title', 'Unknown title'), is_playlist=len(entries) > 1, playlist_index=video.get('playlist_index'))
                queue_manager.add_to_queue(entry)
                await ctx.send(f'Added to queue: {entry.title}')
            else:
                await ctx.send('Error: No audio format available.')

        if queue_was_empty and not ctx.voice_client.is_playing():
            await play_next(ctx)

    async def play_next(ctx):
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
        if queue:
            entry = queue.pop(0)
            queue_manager.save_queues()
            ctx.voice_client.play(discord.FFmpegPCMAudio(entry.video_url), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop))
            await ctx.send(f'Now playing: {entry.title}')

    @bot.command(name='pause')
    async def pause(ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send('Playback paused.')
            logging.info("Playback paused.")

    @bot.command(name='resume')
    async def resume(ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Playback resumed.')
            logging.info("Playback resumed.")

    @bot.command(name='stop')
    async def stop(ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            await ctx.send('Playback stopped and disconnected.')
            logging.info("Playback stopped and bot disconnected.")

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=".", intents=intents)

    @client.event
    async def on_ready():
        logging.info(f'{client.user} is now connected and ready.')

    setup_commands(client)
    client.run(TOKEN)

if __name__ == '__main__':
    run_bot()