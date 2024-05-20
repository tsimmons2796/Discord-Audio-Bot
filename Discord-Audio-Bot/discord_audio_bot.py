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
import random  # Make sure to import the random module

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

async def play_audio(ctx, entry):
    queue_manager.currently_playing = entry
    queue_manager.save_queues()

    def after_playing(error):
        if error:
            logging.error(f"Error playing {entry.title}: {error}")
            asyncio.run_coroutine_threadsafe(ctx.send("Error occurred during playback."), ctx.bot.loop).result()
        else:
            logging.info(f"Finished playing {entry.title}.")
            queue_manager.last_played_audio = entry.title
            queue_manager.save_queues()
            asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop).result()

    if not ctx.voice_client.is_playing():
        ctx.voice_client.play(discord.FFmpegPCMAudio(entry.best_audio_url, options='-bufsize 512k'), after=after_playing)
        await ctx.send(f'Now playing: {entry.title}')

async def play_next(ctx):
    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    if queue and queue_manager.currently_playing:
        current_entry = queue_manager.currently_playing
        if current_entry in queue:
            queue.remove(current_entry)
            queue.append(current_entry)
            queue_manager.save_queues()
        if queue:
            entry = queue[0]
            await play_audio(ctx, entry)

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
        await ctx.send(f"Added to queue: {first_entry.title}")
        await play_audio(ctx, first_entry)
    else:
        await ctx.send("No video found at the specified index.")
        return

    # Fetch the full playlist length for further processing
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

    # Send the current queue summary after all videos are added
    queue = queue_manager.get_queue(datetime.now().strftime('%Y-%m-%d'))
    titles = [entry.title for entry in queue]
    response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
    await ctx.send(response)

async def process_single_video_or_mp3(url, ctx):
    # This function processes a single video or MP3 URL
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
        # await play_audio(ctx, entry)

    bot.remove_command('help')  # Disable the built-in help command

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
    **.previous** - WIP.
    
    **Always taking suggestions for the live service of Radio-Bot**

    Type a command to execute it. For example: `.play https://youtube.com/watch?v=example`
    """
        await ctx.send(help_text)

    @bot.command(name='play_video')
    async def play_video(ctx, *, title: str):
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        
        # Find the index of the entry with the specified title
        entry_index = next((i for i, entry in enumerate(queue) if entry.title == title), None)
        if entry_index is None:
            await ctx.send(f"No video found with title '{title}'.")
            return

        # Move the entry to the front of the queue
        entry = queue.pop(entry_index)
        queue.insert(0, entry)
        
        # Check if something is currently playing and stop it if necessary
        if ctx.voice_client:
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                ctx.voice_client.stop()
                await asyncio.sleep(0.5)  # Wait briefly for the stop action to take effect

        # Ensure the bot is connected to the voice channel
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                return

        # Start playing the requested video
        await play_audio(ctx, entry)
        queue_manager.save_queues()

    @bot.command(name='remove')
    async def remove(ctx, *, title: str):
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await ctx.send("The queue is currently empty.")
            return
        
        # Find and remove the entry by title
        original_length = len(queue)
        queue = [entry for entry in queue if entry.title != title]
        if len(queue) == original_length:
            await ctx.send(f"No track found with title '{title}'.")
        else:
            queue_manager.queues[today_str] = queue  # Update the modified queue
            queue_manager.save_queues()  # Save changes to the queues file
            await ctx.send(f"Removed '{title}' from the queue.")

    @bot.command(name='shuffle')
    async def shuffle(ctx):
        today_str = datetime.now().strftime('%Y-%m-%d')
        queue = queue_manager.get_queue(today_str)
        if not queue:
            await ctx.send("The queue is currently empty.")
            return
        
        # Shuffle the queue in-place
        random.shuffle(queue)
        queue_manager.queues[today_str] = queue  # Update the shuffled queue
        queue_manager.save_queues()  # Save the shuffled queue to the file

        # Prepare a response message with the new order of the queue
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

            # Start playing the requested video
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

        # Check for attached .mp3 files in the message
        if ctx.message.attachments:
            first = True
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith('.mp3'):
                    entry = QueueEntry(
                        video_url=attachment.url,
                        best_audio_url=attachment.url,
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
            # Handle YouTube playlist or single video URLs
            if "list=" in url:  # It's a playlist URL
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
                        break  # Stop processing further if a fetch fails
            else:
                # Handle single video URL or direct MP3
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
            
            # Split the response into chunks of 2000 characters
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

        # Check if the bot is currently playing audio.
        if ctx.voice_client and ctx.voice_client.is_playing():
            current_entry = queue_manager.currently_playing
            if current_entry:
                # Move the current entry to the end of the queue
                queue.remove(current_entry)
                queue.append(current_entry)
                queue_manager.save_queues()
            # Stop the currently playing audio.
            ctx.voice_client.stop()
            await asyncio.sleep(0.5)  # Small delay to ensure the stop command is processed.

        # Proceed to play the next song in the queue.
        if queue:
            # Since the `play_audio` function handles the logic to play the next track,
            # call it directly with the next entry in the queue.
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
