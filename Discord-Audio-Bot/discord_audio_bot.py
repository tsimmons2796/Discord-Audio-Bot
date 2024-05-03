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

logging.basicConfig(level=logging.INFO, filename='queue_log.log')

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
        self.queues: Dict[str, List[QueueEntry]] = self.load_queues()

    def load_queues(self) -> Dict[str, List[QueueEntry]]:
        try:
            with open('queues.json', 'r') as file:
                data = json.load(file)
                return {k: [QueueEntry(**d) for d in v] for k, v in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_queues(self):
        with open('queues.json', 'w') as file:
            json.dump({k: [entry.to_dict() for entry in v] for k, v in self.queues.items()}, file, indent=4)

    def get_queue(self, date_str: str) -> List[QueueEntry]:
        return self.queues.get(date_str, [])

    def add_to_queue(self, entry: QueueEntry):
        date_str = datetime.now().strftime('%m/%d/%Y')
        if date_str not in self.queues:
            self.queues[date_str] = []
        self.queues[date_str].append(entry)
        self.save_queues()

queue_manager = BotQueue()

executor = ThreadPoolExecutor(1)

async def fetch_info(url):
    loop = asyncio.get_running_loop()
    # Run yt_dlp in a separate thread to prevent blocking
    info = await loop.run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
    return info

def setup_commands(bot):
    @bot.command(name='play')
    async def play(ctx, url: str):
        # Ensure the bot is connected to the voice channel
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                return
        
        # Process the YouTube URL
        with yt_dlp.YoutubeDL({'format': 'bestaudio', 'noplaylist': False}) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info['entries'] if 'entries' in info else [info]

            for video in entries:
                if 'formats' in video:
                    video_url = video['formats'][0]['url']
                    entry = QueueEntry(video_url, video.get('title', 'Unknown title'), is_playlist=len(entries) > 1, playlist_index=video.get('playlist_index'))
                    queue_manager.add_to_queue(entry)
                    await ctx.send(f'Added to queue: {entry.title}')
                else:
                    await ctx.send('Error: Could not retrieve format for video.')

            # Start playing the queue if not already playing
            if not ctx.voice_client.is_playing():
                await play_next(ctx)

    async def play_next(ctx):
        date_str = datetime.now().strftime('%m/%d/%Y')
        queue = queue_manager.get_queue(date_str)
        if ctx.voice_client and not ctx.voice_client.is_playing():  # Check if nothing is currently playing
            if queue:
                entry = queue.pop(0)  # Get the next entry
                queue.append(entry)  # Re-append the entry to the end to cycle through the queue
                
                # Fetch the latest audio URL every time before playing
                with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
                    info = ydl.extract_info(entry.video_url, download=False)
                    audio_url = info['url'] if 'url' in info else entry.video_url  # Fallback to the stored URL if no new URL is found
                
                source = discord.FFmpegPCMAudio(audio_url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
                def after_playing(error):
                    if error:
                        print(f"Error: {error}")
                    asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)  # Properly schedule the next play

                ctx.voice_client.play(source, after=after_playing)
                await ctx.send(f'Now playing: {entry.title}')
                queue_manager.save_queues()
            else:
                await ctx.send('The queue is empty.')
        else:
            print("Playback is already in progress or the voice client is not connected.")

    @bot.command(name='pause')
    async def pause(ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send('Playback paused.')

    @bot.command(name='resume')
    async def resume(ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Playback resumed.')

    @bot.command(name='stop')
    async def stop(ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            await ctx.send('Playback stopped and disconnected.')
            
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