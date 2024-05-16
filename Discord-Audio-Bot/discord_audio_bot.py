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
import youtube_dl

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

    def load_queues(self) -> Dict[str, List[QueueEntry]]:
        try:
            with open('queues.json', 'r') as file:
                queues_data = json.load(file)
            return {
                date: [QueueEntry(**entry) for entry in entries]
                for date, entries in queues_data.items()
            }
        except (json.JSONDecodeError, FileNotFoundError) as e:
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
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': False if "list=" in url else True,  # Handle playlists normally only if 'list=' is in the URL
        'playlist_items': str(index) if index is not None else None,  # Fetch specific item if index is provided
        'ignoreerrors': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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

async def play_audio(ctx, entry):
    queue_manager.currently_playing = entry
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

async def play_next(ctx):
    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    if queue and queue_manager.currently_playing:
        # Move current track to the end
        current_entry = queue.pop(0)
        queue.append(current_entry)
        queue_manager.save_queues()
        # Play next available entry
        entry = queue[0]  # Get the next entry
        await play_audio(ctx, entry)

def setup_commands(bot):
    @bot.command(name='play_queue')
    async def play_queue(ctx):
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
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

            # Play the audio using FFmpeg, handling both YouTube and direct MP3 URLs.
            ffmpeg_options = {
                'options': '-vn',  # no video
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
            }
            ctx.voice_client.play(discord.FFmpegPCMAudio(entry.best_audio_url, **ffmpeg_options), after=lambda e: print(f'Finished playing: {entry.title}'))
            await ctx.send(f'Now playing: {entry.title}')

            # Move the current track to the end of the queue and save the queue state
            current_entry = queue.pop(0)
            queue.append(current_entry)
            queue_manager.save_queues()
        else:
            await ctx.send("Queue is empty.")

    @bot.command(name='play')
    async def play(ctx, url: str = None):
        # Setup the voice client connection
        voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not voice_client and ctx.author.voice:
            voice_client = await ctx.author.voice.channel.connect()
        elif not ctx.author.voice:
            await ctx.send("You are not connected to a voice channel.")
            return

        entry = None

        # Check for attached .mp3 files in the message
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.filename.lower().endswith('.mp3'):
                entry = QueueEntry(
                    video_url=attachment.url,
                    best_audio_url=attachment.url,
                    title=attachment.filename,
                    is_playlist=False,
                    playlist_index=None
                )
                queue_manager.add_to_queue(entry)
                if not voice_client.is_playing():
                    await play_audio(ctx, entry)
                else:
                    await ctx.send(f"'{entry.title}' added to the queue.")
            else:
                await ctx.send("Attached file is not a supported MP3 file.")
            return

        # Handle YouTube playlist or single video URLs
        if url:
            if "list=" in url:  # URL is a playlist
                playlist_length = await fetch_playlist_length(url)
                for index in range(1, playlist_length + 1):
                    video_info = await fetch_info(url, index)
                    if video_info and 'entries' in video_info and video_info['entries']:
                        video = video_info['entries'][0]
                        entry = QueueEntry(
                            video_url=video.get('webpage_url', ''),
                            best_audio_url=next((f['url'] for f in video['formats'] if f.get('acodec') != 'none'), ''),
                            title=video.get('title', 'Unknown title'),
                            is_playlist=True,
                            playlist_index=index
                        )
                        queue_manager.add_to_queue(entry)
                        if index == 1 or not voice_client.is_playing():
                            await play_audio(ctx, entry)
                    else:
                        await ctx.send(f"Could not retrieve video at index {index}.")
                        break
            else:  # URL is a single video or direct MP3 URL
                video_info = await fetch_info(url)
                if video_info:
                    entry = QueueEntry(
                        video_url=video_info.get('webpage_url', url),
                        best_audio_url=next((f['url'] for f in video_info['formats'] if f.get('acodec') != 'none'), url),
                        title=video_info.get('title', url.split('/')[-1]),
                        is_playlist=False
                    )
                    queue_manager.add_to_queue(entry)
                    if not voice_client.is_playing():
                        await play_audio(ctx, entry)
                    else:
                        await ctx.send(f"'{entry.title}' added to the queue.")
        else:
            await ctx.send("Please provide a valid URL or attach an MP3 file.")

        
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
            if index == 1:  # Play the first video immediately
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

    @bot.command(name='play-queue')
    async def play_queue(ctx):
        await ctx.send('Queue Load Started')
        await play_next(ctx)
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
        queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
        if not queue:
            await ctx.send("Queue is empty.")
            return

        # Check if the bot is currently playing audio.
        if ctx.voice_client and ctx.voice_client.is_playing():
            # Stop the currently playing audio.
            ctx.voice_client.stop()
            await asyncio.sleep(0.5)  # Small delay to ensure the stop command is processed.

        # Proceed to play the next song in the queue.
        if len(queue) > 0:
            # As the `play_audio` function itself handles the logic to play the next track
            # from the `after_playing` callback, and updates the `currently_playing` correctly,
            # we just call it directly for the next in queue without popping it here.
            await play_audio(ctx, queue[0])
        else:
            await ctx.send("No more tracks to skip to.")


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
