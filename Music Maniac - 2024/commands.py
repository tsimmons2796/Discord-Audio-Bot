import discord  # Discord API wrapper for building bots
import logging  # Library for logging events for debugging
import asyncio  # Asynchronous I/O to handle asynchronous operations
import yt_dlp  # YouTube downloading library supporting various sites
import random
import os
import threading
import json

# Global dictionaries to manage voice clients and song queues for each Discord server (guild)
voice_clients = {}
# queues = {}
# history = {}  # Dictionary to keep track of played songs

QUEUE_FILE_PATH = 'C:\\Users\\Travis\\Documents\\Python\\YT-Discord-Bot\\Music Maniac - 2024\\yt-bot-queue.json'
HISTORY_FILE_PATH = 'C:\\Users\\Travis\\Documents\\Python\\YT-Discord-Bot\\Music Maniac - 2024\\yt-bot-queue.json'


# Configuration for downloading from YouTube, focusing on fetching the best audio quality available
yt_dl_options = {"format": "bestaudio/best", 'noplaylist': False}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

# Configuration for FFmpeg
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.75"'
}

def load_data_from_json(file_path):
    try:
        with open(file_path, 'r') as file:
            data = file.read()
            if data:  # Ensure the file is not empty
                return json.loads(data)
            else:
                return {}  # Return an empty dictionary if the file is empty
    except FileNotFoundError:
        return {}  # Return an empty dictionary if the file does not exist
    except json.JSONDecodeError:
        logging.error(f"JSON decode error in file {file_path}. Starting with an empty dictionary.")
        return {}  # Return an empty dictionary if there is a decoding error

def save_data_to_json(data, file_path):
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
    except IOError as e:
        logging.error(f"Failed to write to file {file_path}: {e}")

def update_queue(guild_id, song):
    queues.setdefault(guild_id, [])
    queues[guild_id].append(song)
    save_data_to_json(queues, QUEUE_FILE_PATH)

def update_history(guild_id, song):
    history.setdefault(guild_id, {'songs': [], 'current_index': -1})
    history[guild_id]['songs'].append(song)
    history[guild_id]['current_index'] += 1
    save_data_to_json(history, HISTORY_FILE_PATH)

queues = load_data_from_json(QUEUE_FILE_PATH)
history = load_data_from_json(HISTORY_FILE_PATH)

def extract_songs(link):
    """Extracts songs from a given link and returns them as a list."""
    options = yt_dl_options.copy()
    ytdl = yt_dlp.YoutubeDL(options)
    data = ytdl.extract_info(link, download=False)
    songs = []
    if 'entries' in data:
        # Handle playlists
        songs = [{'url': entry['url'], 'title': entry.get('title', 'No title available')} for entry in data['entries']]
    else:
        # Handle single video
        songs.append({'url': data['url'], 'title': data.get('title', 'No title available')})
    return songs


def setup_commands(client):
    @client.command(name="play")
    async def play(ctx, link):
        if not ctx.author.voice:
            await ctx.send("Please join a voice channel first.")
            return
        voice_client = voice_clients.get(ctx.guild.id) or await connect_voice_client(ctx)
        if not voice_client:
            return

        # Extract songs from the provided link
        songs = extract_songs(link)
        if not songs:
            await ctx.send("No songs found at the provided link.")
            return

        # Update the queue with new songs and save to JSON
        guild_id = ctx.guild.id
        queue = load_data_from_json(QUEUE_FILE_PATH).get(guild_id, [])
        queue.extend(songs)
        queues[guild_id] = queue
        save_data_to_json(queues, QUEUE_FILE_PATH)

        # Send messages about added songs
        for song in songs:
            await ctx.send(f"Added to queue: {song['title']}")

        # Optionally start playback if nothing is currently playing
        if not voice_client.is_playing():
            await play_next(ctx)
    
    async def handle_playback(ctx, voice_client, link):
        """Manages the playback of songs from a link, starting with the first song and then loading the rest."""
        from queue import Queue
        song_queue = Queue()
        threading.Thread(target=extract_songs, args=(link, song_queue, True)).start()  # Fetch the first song quickly in a separate thread
        while song_queue.empty():
            await asyncio.sleep(0.1)  # Non-blocking sleep while waiting for the first song
        first_song = song_queue.get()
        await play_song(ctx, voice_client, first_song)  # Play the first song immediately
        threading.Thread(target=extract_songs, args=(link, song_queue)).start()  # Continue fetching the rest in the background
        while True:
            while not song_queue.empty():
                song = song_queue.get()
                queues.setdefault(ctx.guild.id, []).append(song)
                await ctx.send(f"Added to queue: {song['title']}")
            await asyncio.sleep(1)

    @client.command(name="previous")
    async def previous(ctx):
        """Plays the last song from the history, if available."""
        if ctx.guild.id in history and history[ctx.guild.id]['songs']:
            # Decrease the current index to get the previous song, ensuring not to go below zero
            history[ctx.guild.id]['current_index'] = max(0, history[ctx.guild.id]['current_index'] - 1)
            
            # Fetch the song using the current index
            last_song = history[ctx.guild.id]['songs'][history[ctx.guild.id]['current_index']]
            await play_song(ctx, voice_clients[ctx.guild.id], last_song)
            await ctx.send(f"Playing the previous song: {last_song['title']}")
        else:
            await ctx.send("No previous song to play.")
            logging.info("No previous song available to play.")

    async def connect_voice_client(ctx):
        """Attempts to connect the bot to the voice channel of the command issuer."""
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
            logging.info(f"Connected to voice channel in guild {ctx.guild.id}.")
            return voice_client
        except Exception as e:
            logging.error(f"Failed to connect to voice channel: {e}")
            await ctx.send("Failed to connect to voice channel.")
            return None

    async def play_song(ctx, voice_client, song_data):
        """Plays a song using the provided voice client."""
        try:
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
                await asyncio.sleep(1000)  # Wait to ensure the player has stopped

            player = discord.FFmpegOpusAudio(song_data['url'], **ffmpeg_options)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
            logging.info(f"Started playing: {song_data['title']}")
            await ctx.send(f"Playing: {song_data['title']}")
        except Exception as e:
            logging.error(f"Error during playback: {e}. URL: {song_data['url']}, Options: {ffmpeg_options}")
            await ctx.send("Error during playback. Check the logs for more details.")

    async def play_next(ctx):
        """Plays the next song in the queue, if available."""
        guild_id = ctx.guild.id
        queue = load_data_from_json(QUEUE_FILE_PATH).get(guild_id, [])
        if queue:
            next_song = queue.pop(0)
            await play_song(ctx, voice_clients[guild_id], next_song)
            # Save the updated queue
            save_data_to_json({guild_id: queue}, QUEUE_FILE_PATH)
        else:
            await ctx.send("Queue is empty.")
            logging.info("Queue empty, disconnected from voice channel.")
            await disconnect_voice_client(ctx)

    async def disconnect_voice_client(ctx):
        """Disconnects the bot from the voice channel and cleans up resources."""
        if ctx.guild.id in voice_clients:
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            logging.info(f"Disconnected from voice channel in guild {ctx.guild.id}.")

    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        """Clears the current music queue for the guild."""
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
            logging.info(f"Queue cleared for guild {ctx.guild.id}.")
        else:
            await ctx.send("There is no queue to clear!")
            logging.info(f"No queue to clear for guild {ctx.guild.id}.")

    @client.command(name="skip")
    async def skip(ctx):
        """Skips the currently playing song and starts the next song in the queue, if available."""
        if ctx.guild.id in voice_clients:
            voice_client = voice_clients[ctx.guild.id]
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
                # Wait a moment to ensure the player has fully stopped
                await asyncio.sleep(1000)  # Adjust this based on empirical testing

                logging.info(f"Current song in guild {ctx.guild.id} has been stopped.")
                # Ensure there's another song to play
                if queues[ctx.guild.id]:
                    next_song = queues[ctx.guild.id].pop(0)
                    await play_song(ctx, voice_client, next_song)
                    logging.info(f"Playing next song: {next_song['title']}")
                else:
                    await ctx.send("The queue is now empty.")
                    logging.info("No more songs in the queue to play.")
            else:
                await ctx.send("No song is currently playing.")
                logging.info("Skip command issued but no song was playing.")
        else:
            await ctx.send("The bot is not connected to a voice channel.")
            logging.error(f"No voice client found for guild {ctx.guild.id}.")

    @client.command(name="pause")
    async def pause(ctx):
        """Pauses the current playback if something is playing."""
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
            voice_clients[ctx.guild.id].pause()
            logging.info(f"Playback paused in guild {ctx.guild.id}.")
            await ctx.send("Playback paused.")
        else:
            await ctx.send("Nothing is currently playing.")
            logging.warning(f"Attempt to pause playback failed in guild {ctx.guild.id}.")

    @client.command(name="resume")
    async def resume(ctx):
        """Resumes playback if it was paused."""
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_paused():
            voice_clients[ctx.guild.id].resume()
            logging.info(f"Playback resumed in guild {ctx.guild.id}.")
            await ctx.send("Playback resumed.")
        else:
            await ctx.send("There is nothing to resume.")
            logging.warning(f"Attempt to resume playback failed in guild {ctx.guild.id}.")

    @client.command(name="stop")
    async def stop(ctx):
        """Stops playback completely and disconnects the bot from the voice channel."""
        if ctx.guild.id in voice_clients:
            voice_clients[ctx.guild.id].stop()
            await disconnect_voice_client(ctx)
            logging.info(f"Playback stopped and disconnected in guild {ctx.guild.id}.")
            await ctx.send("Playback stopped and disconnected.")
        else:
            await ctx.send("The bot is not connected to a voice channel.")
            logging.error(f"Attempt to stop playback failed in guild {ctx.guild.id}.")
    @client.command(name="shuffle")
    async def shuffle(ctx):
        """Shuffles the current queue randomly."""
        guild_id = ctx.guild.id
        if guild_id in queues and queues[guild_id]:
            random.shuffle(queues[guild_id])
            await ctx.send("Queue shuffled!")
            logging.info(f"Queue shuffled for guild {guild_id}.")
        else:
            await ctx.send("No queue to shuffle.")
            logging.info(f"No queue found to shuffle for guild {guild_id}.")


    @client.command(name="queue")
    async def queue(ctx, url):
        # Add a single song to the queue directly
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")
        logging.info(f"Added URL to queue for guild {ctx.guild.id}: {url}")
            
    # @client.command(name="list-queue")
    # async def list_queue(ctx):
    #     """
    #     This command lists all the songs currently queued up in the guild's queue.
    #     It splits the message into several parts if the total length exceeds Discord's limit of 2000 characters per message.
    #     """
    #     guild_id = ctx.guild.id  # Get the guild ID where the command was invoked
    #     logging.info(f"Listing queue for guild {guild_id}. Attempting to retrieve queue data.")

    #     if guild_id in queues and queues[guild_id]:
    #         # Initialize a list to store parts of the final message if needed
    #         messages = []
    #         current_message = "Current queue:\n"
    #         logging.debug(f"Initialized message building for guild {guild_id}. Queue size: {len(queues[guild_id])}")

    #         # Iterate through each song in the queue
    #         for index, song in enumerate(queues[guild_id], 1):
    #             entry = f"{index}. {song['title']}\n"  # Prepare entry string for the message
    #             logging.debug(f"Preparing to add song to message: {song['title']}")

    #             # Check if adding the next entry will exceed the Discord message length limit of 2000 characters
    #             if len(current_message) + len(entry) > 2000:
    #                 messages.append(current_message)  # Append the current message to the list of messages
    #                 current_message = entry  # Start a new message with the current song entry
    #                 logging.debug(f"Message split for guild {guild_id}. New message started due to length.")
    #             else:
    #                 current_message += entry  # Add the song entry to the current message

    #         messages.append(current_message)  # Add the last message segment to the list

    #         # Send each part of the message
    #         for message in messages:
    #             await ctx.send(message)  # Send each part of the message
    #             logging.info(f"Displayed part of the queue for guild {guild_id}. Message length: {len(message)}")
    #     else:
    #         # Inform the user that the queue is currently empty
    #         await ctx.send("The queue is currently empty.")
    #         logging.info(f"No queue to display for guild {guild_id}. Queue is empty.")
    @client.command(name="list-queue")
    async def list_queue(ctx):
        queue = load_data_from_json(QUEUE_FILE_PATH).get(ctx.guild.id, [])
        if queue:
            message = "Current queue:\n" + "\n".join(f"{idx + 1}. {song['title']}" for idx, song in enumerate(queue))
            await ctx.send(message)
        else:
            await ctx.send("The queue is currently empty.")