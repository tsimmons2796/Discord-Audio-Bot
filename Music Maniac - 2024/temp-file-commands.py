import discord  # Discord API wrapper for building bots
import logging  # Library for logging events for debugging
import asyncio  # Asynchronous I/O to handle asynchronous operations
import yt_dlp  # YouTube downloading library supporting various sites
import random
import os
import threading
from queue import Queue
# Global dictionaries to manage voice clients and song queues for each Discord server (guild)
voice_clients = {}
queues = {}
song_queue = Queue()
history = {}  # Dictionary to keep track of played songs

# Configuration for downloading from YouTube, focusing on fetching the best audio quality available
yt_dl_options = {"format": "bestaudio/best", "noplaylist": True}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

# Configuration for FFmpeg
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.75"'
}

def extract_songs(link, queue, fetch_first_only=False):
    options = yt_dl_options.copy()
    if fetch_first_only:
        options['playlistend'] = 1  # Fetch only the first item for immediate playback

    ytdl = yt_dlp.YoutubeDL(options)
    data = ytdl.extract_info(link, download=True)
    # data = ytdl.extract_info(link, download=False)
    print(data)
    if 'entries' in data:
        for entry in data['entries']:
            queue.put({'url': entry['url'], 'title': entry.get('title', 'No title available')})
    else:
        queue.put({'url': data['url'], 'title': data.get('title', 'No title available')})

def setup_commands(client):
    @client.command(name="play")
    async def play(ctx, link):
        if not ctx.author.voice:
            await ctx.send("Please join a voice channel first.")
            return

        voice_client = voice_clients.get(ctx.guild.id) or await connect_voice_client(ctx)
        if not voice_client:
            logging.info("Voice client not available.")
            return

        logging.info(f"Starting to handle playback for link: {link}")
        client.loop.create_task(handle_playback(ctx, voice_client, link))
    
    async def handle_playback(ctx, voice_client, link):
        # from queue import Queue
        # song_queue = Queue()
        
        # Start a separate thread to fetch only the first song quickly
        threading.Thread(target=extract_songs, args=(link, song_queue, True)).start()

        # Wait for the first song and play it
        while song_queue.empty():
            await asyncio.sleep(0.1)  # Non-blocking sleep
        first_song = song_queue.get()
        await play_song(ctx, voice_client, first_song)

        # Continue fetching the rest in the background
        threading.Thread(target=extract_songs, args=(link, song_queue)).start()

        # Handle the rest of the songs as they are extracted
        while True:
            while not song_queue.empty():
                song = song_queue.get()
                queues.setdefault(ctx.guild.id, []).append(song)
                await ctx.send(f"Added to queue: {song['title']}")
            await asyncio.sleep(1)
        
    @client.command(name="previous")
    async def previous(ctx):
        if ctx.guild.id in history and history[ctx.guild.id]:
            last_song = history[ctx.guild.id].pop()  # Remove the last played song from history
            await play(ctx, last_song)  # Play the last song
            await ctx.send("Playing the previous song...")
        else:
            await ctx.send("No previous song to play.")

    async def connect_voice_client(ctx):
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
            return voice_client
        except Exception as e:
            logging.error(f"Failed to connect to voice channel: {e}")
            await ctx.send("Failed to connect to voice channel.")
            return None

    async def extract_song_data(link):
        logging.info(f"Starting extraction for link: {link}")
        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
        if 'entries' in data:
            for entry in data['entries']:
                if 'url' in entry:
                    song_data = {'url': entry['url'], 'title': entry.get('title', 'No title available')}
                    logging.info(f"Yielding song data: {entry.get('title', 'No title available')}")
                    yield song_data
        else:
            if 'url' in data:
                song_data = {'url': data['url'], 'title': data.get('title', 'No title available')}
                logging.info(f"Yielding single video data: {data.get('title', 'No title available')}")
                yield song_data


    async def play_song(ctx, voice_client, song_data):
        try:
            player = discord.FFmpegOpusAudio(song_data['url'], **ffmpeg_options)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
            logging.info(f"Started playing: {song_data['title']}")
            await ctx.send(f"Playing: {song_data['title']}")
        except Exception as e:
            logging.error(f"Error during playback: {e}")
            await ctx.send("Error during playback.")

    async def play_next(ctx):
        if queues[ctx.guild.id]:
            next_song = queues[ctx.guild.id].pop(0)
            history.setdefault(ctx.guild.id, []).append(next_song)
            await play_song(ctx, voice_clients[ctx.guild.id], next_song)
        else:
            await disconnect_voice_client(ctx)

    async def connect_voice_client(ctx):
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
            return voice_client
        except Exception as e:
            logging.error(f"Failed to connect to voice channel: {e}")
            await ctx.send("Failed to connect to voice channel.")
            return None

    async def disconnect_voice_client(ctx):
        if ctx.guild.id in voice_clients:
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            logging.info(f"Disconnected from voice channel in guild {ctx.guild.id}.")

    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
            logging.info(f"Queue cleared for guild {ctx.guild.id}.")
        else:
            await ctx.send("There is no queue to clear!")
            logging.info(f"No queue to clear for guild {ctx.guild.id}.")
    @client.command(name="skip")
    async def skip(ctx):
        # Check if the bot is connected to the voice channel
        if ctx.guild.id in voice_clients:
            # Stop the current song and play the next
            voice_client = voice_clients[ctx.guild.id]
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
                logging.info(f"Skipped current song in guild {ctx.guild.id}.")
                await play_next(ctx)
            else:
                await ctx.send("No song is currently playing.")
        else:
            await ctx.send("The bot is not connected to a voice channel.")
            logging.error(f"No voice client found for guild {ctx.guild.id}.")

    @client.command(name="pause")
    async def pause(ctx):
        # Pause current playback
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
            voice_clients[ctx.guild.id].pause()
            logging.info(f"Playback paused in guild {ctx.guild.id}.")
            await ctx.send("Playback paused.")
        else:
            await ctx.send("Nothing is currently playing.")
            logging.warning(f"Attempt to pause playback failed in guild {ctx.guild.id}.")

    @client.command(name="resume")
    async def resume(ctx):
        # Resume playback if it was paused
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_paused():
            voice_clients[ctx.guild.id].resume()
            logging.info(f"Playback resumed in guild {ctx.guild.id}.")
            await ctx.send("Playback resumed.")
        else:
            await ctx.send("There is nothing to resume.")
            logging.warning(f"Attempt to resume playback failed in guild {ctx.guild.id}.")

    @client.command(name="stop")
    async def stop(ctx):
        # Stop playback and disconnect the bot from the voice channel
        if ctx.guild.id in voice_clients:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            logging.info(f"Playback stopped and disconnected in guild {ctx.guild.id}.")
            await ctx.send("Playback stopped and disconnected.")
        else:
            await ctx.send("The bot is not connected to a voice channel.")
            logging.error(f"Attempt to stop playback failed in guild {ctx.guild.id}.")


    @client.command(name="queue")
    async def queue(ctx, url):
        # Add a single song to the queue directly
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")
        logging.info(f"Added URL to queue for guild {ctx.guild.id}: {url}")

    @client.command(name="download_channel")
    async def download_channel(ctx, url):
        if url.startswith(('https://www.youtube.com/c/', 'https://www.youtube.com/channel/', 'https://www.youtube.com/user/')):
            await ctx.send("Starting channel download...")
            ydl_opts = {
                'ignoreerrors': True,
                'format': 'best[ext=mp4]',
                'outtmpl': os.path.join(download_path, 'Channels', '%(uploader)s', '%(title)s ## %(uploader)s ## %(id)s.%(ext)s'),
                'ratelimit': 5000000,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            await ctx.send("Channel download completed.")
        else:
            await ctx.send("Invalid channel URL provided.")

    @client.command(name="download_playlist")
    async def download_playlist(ctx, url):
        if url.startswith('https://www.youtube.com/playlist'):
            await ctx.send("Starting playlist download...")
            ydl_opts = {
                'ignoreerrors': True,
                'format': 'best[ext=mp4]',
                'outtmpl': os.path.join(download_path, 'Playlists', '%(playlist_uploader)s', '%(playlist)s', '%(title)s ## %(uploader)s ## %(id)s.%(ext)s'),
                'ratelimit': 5000000,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            await ctx.send("Playlist download completed.")
        else:
            await ctx.send("Invalid playlist URL provided.")

    @client.command(name="download_video")
    async def download_video(ctx, url):
        if url.startswith(('https://www.youtube.com/watch', 'https://www.twitch.tv/', 'https://clips.twitch.tv/')):
            await ctx.send("Starting video download...")
            ydl_opts = {
                'ignoreerrors': True,
                'format': 'best[ext=mp4]',
                'outtmpl': os.path.join(download_path, 'Videos', '%(title)s ## %(uploader)s ## %(id)s.%(ext)s'),
                'ratelimit': 5000000,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            await ctx.send("Video download completed.")
        else:
            await ctx.send("Invalid video URL provided.")
    @client.command(name="shuffle")
    async def shuffle(ctx):
        guild_id = ctx.guild.id
        if guild_id in queues and queues[guild_id]:
            random.shuffle(queues[guild_id])
            await ctx.send("Queue shuffled!")
            logging.info(f"Queue shuffled for guild {guild_id}.")
        else:
            await ctx.send("No queue to shuffle.")
            logging.info(f"No queue found to shuffle for guild {guild_id}.")
            
    @client.command(name="list-queue")
    async def list_queue(ctx):
        guild_id = ctx.guild.id
        if guild_id in queues and queues[guild_id]:
            # Building the queue message
            messages = []
            current_message = "Current queue:\n"
            for index, song in enumerate(queues[guild_id], 1):
                entry = f"{index}. {song['title']}\n"  # Only display the song title
                # Check if adding the next entry will exceed the Discord message length limit of 2000 characters
                if len(current_message) + len(entry) > 2000:
                    messages.append(current_message)
                    current_message = entry  # Start a new message
                else:
                    current_message += entry

            messages.append(current_message)  # Add the last message segment

            for message in messages:
                await ctx.send(message)  # Send each part of the message
                logging.info(f"Displayed part of the queue for guild {guild_id}.")
        else:
            await ctx.send("The queue is currently empty.")
            logging.info(f"No queue to display for guild {guild_id}.")
            
            
            
#             import discord  # Discord API wrapper for building bots
# import logging  # Library for logging events for debugging
# import asyncio  # Asynchronous I/O to handle asynchronous operations
# import yt_dlp  # YouTube downloading library supporting various sites
# import random
# import os
# import threading
# from queue import Queue
# # Global dictionaries to manage voice clients and song queues for each Discord server (guild)
# voice_clients = {}
# queues = {}
# song_queue = Queue()
# history = {}  # Dictionary to keep track of played songs

# # Configuration for downloading from YouTube, focusing on fetching the best audio quality available
# yt_dl_options = {"format": "bestaudio/best", "noplaylist": False}
# ytdl = yt_dlp.YoutubeDL(yt_dl_options)

# # Configuration for FFmpeg
# ffmpeg_options = {
#     'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
#     'options': '-vn -filter:a "volume=0.75"'
# }
# def extract_playlist_info(link):
#     options = {
#         'format': 'bestaudio/best',
#         'noplaylist': False,
#         'quiet': True,
#         'extract_flat': 'in_playlist',
#         'ignoreerrors': True
#     }
#     with yt_dlp.YoutubeDL(options) as ytdl:
#         data = ytdl.extract_info(link, download=False)
#         entries_info = []
#         if 'entries' in data:
#             for index, entry in enumerate(data['entries']):
#                 entry_info = {
#                     'index': index,
#                     'title': entry.get('title', 'No title available'),
#                     'url': entry.get('webpage_url', 'No URL available')
#                 }
#                 entries_info.append(entry_info)
#                 logging.debug(f"Retrieved entry: {entry_info}")
#             return {'playlist_title': data.get('title'), 'count': len(data['entries']), 'entries': entries_info}
#         else:
#             single_entry = {
#                 'index': 0,
#                 'title': data.get('title'),
#                 'url': data.get('webpage_url'),
#                 'count': 1
#             }
#             logging.debug(f"Retrieved single video: {single_entry}")
#             return single_entry


# def extract_songs(link):
#     """ Extracts songs information from the given link. It returns the count of songs and their titles if it's a playlist. """
#     with yt_dlp.YoutubeDL(yt_dl_options) as ytdl:
#         data = ytdl.extract_info(link, download=False)
#         if 'entries' in data:
#             song_titles = [entry.get('title', 'No title available') for entry in data['entries']]
#             return len(data['entries']), song_titles
#         else:
#             return 1, [data.get('title', 'No title available')]

# def setup_commands(client):
#     @client.command(name="play")
#     async def play(ctx, link: str):
#         logging.info(f"Command !play called with link: {link}")
#         if not ctx.author.voice:
#             await ctx.send("Please join a voice channel first.")
#             return

#         voice_client = voice_clients.get(ctx.guild.id) or await connect_voice_client(ctx)
#         if not voice_client:
#             await ctx.send("Could not connect to the voice channel.")
#             return

#         playlist_info = extract_playlist_info(link)
#         if playlist_info['count'] == 0:
#             await ctx.send("No playable entries found.")
#             return

#         queues.setdefault(ctx.guild.id, [])
#         for entry in playlist_info['entries']:
#             queues[ctx.guild.id].append(entry)
#             logging.debug(f"Added to queue: {entry}")

#         await ctx.send(f"Added {playlist_info['count']} songs to the queue.")
#         if not voice_client.is_playing():
#             await play_next(ctx)
#     @client.command(name="list-queue")
#     async def list_queue(ctx):
#         guild_id = ctx.guild.id
#         logging.info(f"Checking queue for guild: {guild_id}")
#         if guild_id in queues:
#             if queues[guild_id]:
#                 messages = ["Current queue:"]
#                 current_message = ""
#                 for index, song in enumerate(queues[guild_id], 1):
#                     entry = f"{index}. {song['title']} (URL: {song['url']})\n"
#                     if len(current_message) + len(entry) > 1900:
#                         messages.append(current_message)
#                         current_message = entry
#                     else:
#                         current_message += entry
#                 if current_message:
#                     messages.append(current_message)
#                 for message in messages:
#                     await ctx.send(message)
#                 logging.info(f"Queue for guild {guild_id} displayed successfully.")
#             else:
#                 await ctx.send("The queue is currently empty.")
#                 logging.info(f"Queue for guild {guild_id} is empty.")
#         else:
#             await ctx.send("No queue found for this guild.")
#             logging.info(f"No queue initialized for guild {guild_id}.")

#     async def play_song(ctx, voice_client, song_data):
#         try:
#             player = discord.FFmpegOpusAudio(song_data['url'], **ffmpeg_options)
#             voice_client.play(player, after=lambda e: song_finished(e, ctx))
#             logging.info(f"Started playing: {song_data['title']} URL: {song_data['url']}")
#         except Exception as e:
#             logging.error(f"Error during playback: {e}", exc_info=True)
#             await ctx.send("Error during playback.")

#     def song_finished(error, ctx):
#         if error:
#             logging.error(f"Playback error: {error}", exc_info=True)
#         asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop)
#         logging.info(f"Song finished, loading next in guild {ctx.guild.id}")

#     async def play_next(ctx):
#         guild_id = ctx.guild.id
#         if guild_id in queues and queues[guild_id]:
#             if queues[guild_id]:
#                 next_song = queues[guild_id].pop(0)
#                 history.setdefault(guild_id, []).append(next_song)
#                 logging.info(f"Playing next song: {next_song['title']} from queue in guild {guild_id}")
#                 await play_song(ctx, voice_clients[guild_id], next_song)
#             else:
#                 logging.info(f"Queue empty after song finished in guild {guild_id}")
#         else:
#             await disconnect_voice_client(ctx)
#             logging.info(f"Queue is empty or not found, disconnected from voice channel in guild {guild_id}")

#         logging.debug(f"Queue Status for {guild_id}: {queues[guild_id]} (after attempting to play next song)")

#     async def connect_voice_client(ctx):
#         try:
#             voice_client = await ctx.author.voice.channel.connect()
#             voice_clients[ctx.guild.id] = voice_client
#             logging.info(f"Connected to voice channel in guild {ctx.guild.id}")
#             return voice_client
#         except Exception as e:
#             logging.error("Failed to connect to voice channel", exc_info=True)
#             return None

#     async def disconnect_voice_client(ctx):
#         guild_id = ctx.guild.id
#         if guild_id in voice_clients:
#             await voice_clients[guild_id].disconnect()
#             del voice_clients[guild_id]
#             logging.info(f"Disconnected from voice channel in guild {guild_id}")