# Import required libraries
import discord  # Discord API wrapper for building bots
import logging  # Library for logging events for debugging
import asyncio  # Asynchronous I/O to handle asynchronous operations
import yt_dlp  # YouTube downloading library supporting various sites

# Global dictionaries to manage voice clients and song queues for each Discord server (guild)
voice_clients = {}
queues = {}

# Configuration for downloading from YouTube, focusing on fetching the best audio quality available
yt_dl_options = {"format": "bestaudio/best"}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)  # Initialize YouTube downloader with specified options

# Configuration for FFmpeg, a multimedia framework to decode, encode, transcode, mux, demux, stream, filter and play almost anything
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',  # Options to handle disconnections
    'options': '-vn -filter:a "volume=0.25"'  # Disable video processing and adjust audio volume
}

def setup_commands(client):
    """
    Defines all commands and functionalities for the Discord bot.
    
    :param client: The discord bot client instance used to interact with the Discord servers.
    """

    # Function to handle playing the next song in the queue
    async def play_next(ctx):
        # Check if there are songs left in the queue; if so, play the next
        if queues[ctx.guild.id]:
            link = queues[ctx.guild.id].pop(0)  # Remove the first song from the queue and save it
            logging.info(f"Playing next in queue for guild {ctx.guild.id}: {link}")
            await play(ctx, link)  # Play the next song
        else:
            # If the queue is empty, wait a designated period before disconnecting from the voice channel (5 Minutes)
            wait_seconds = 300
            await asyncio.sleep(wait_seconds)  # Pause execution for wait_seconds
            if not queues[ctx.guild.id]:  # Recheck if the queue is still empty
                if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
                    await voice_clients[ctx.guild.id].disconnect()  # Disconnect the bot from the voice channel
                    del voice_clients[ctx.guild.id]  # Remove the client from tracking to clean up
                    logging.info(f"Disconnected from voice channel in guild {ctx.guild.id} due to empty queue.")

    @client.command(name="play")
    async def play(ctx, link):
        # Check if the command issuer is in a voice channel
        if ctx.author.voice is None:
            await ctx.send("Get in a voice channel first...")
            logging.warning("Attempt to play music without being in a voice channel.")
            return

        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []  # Initialize the queue if it does not exist

        # Check if the bot is already connected to the voice channel
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
            logging.info("Bot is already connected to the voice channel.")
            voice_client = voice_clients[ctx.guild.id]
        else:
            try:
                voice_client = await ctx.author.voice.channel.connect()  # Connect to the user's voice channel
                voice_clients[ctx.guild.id] = voice_client
                logging.info(f"Connected to voice channel in guild {ctx.guild.id}")
            except Exception as e:
                logging.error(f"Error connecting to voice channel: {e}")
                return

        try:
            loop = asyncio.get_event_loop()
            # Handle playlists differently from individual songs
            if "playlist" in link:
                # Fetch playlist info without downloading
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False, process=False))
                first_entry = data.get('entries', [])[0] if data.get('entries') else None
                if first_entry:
                    # Start playing the first video of the playlist immediately
                    first_video_url = await loop.run_in_executor(None, lambda: ytdl.extract_info(first_entry['url'], download=False))
                    first_song = first_video_url['url']
                    if not (voice_client.is_playing() or voice_client.is_paused()):
                        player = discord.FFmpegOpusAudio(first_song, **ffmpeg_options)
                        voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
                        logging.info(f"Immediate playback of first playlist item started: {first_song}")
                        await ctx.send("Playing first video of the playlist.")
                    # Queue the rest of the playlist entries
                    asyncio.create_task(queue_playlist(ctx, data['entries'][1:]))
                else:
                    await ctx.send("No videos found in the playlist.")
                    logging.info("No videos found in the playlist.")
            else:
                # Handle a single video
                song_data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
                song = song_data['url']
                logging.info(f"Extracted URL for playback: {song}")
                if voice_client.is_playing() or voice_client.is_paused():
                    queues[ctx.guild.id].append(song)
                    logging.info(f"Added to queue as something is already playing in guild {ctx.guild.id}: {song}")
                    await ctx.send("Added to queue!")
                else:
                    player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
                    voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
                    logging.info("Playback started.")
        except Exception as e:
            logging.error(f"Failed to handle video data: {e}")

    async def queue_playlist(ctx, entries):
        # Queue each entry in a playlist after the first
        for entry in entries:
            video_url = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(entry['url'], download=False))
            queues[ctx.guild.id].append(video_url['url'])
        logging.info(f"Added {len(entries)} videos to queue from playlist.")
        await ctx.send(f"Added {len(entries)} videos to queue from playlist.")

    # Commands for managing the queue and controlling playback
    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        # Clear the music queue for the server
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
            logging.info(f"Queue cleared for guild {ctx.guild.id}.")
        else:
            await ctx.send("There is no queue to clear!")
            logging.info(f"No queue to clear for guild {ctx.guild.id}.")

    @client.command(name="skip")
    async def skip(ctx):
        # Skip the current song and play the next
        voice_clients[ctx.guild.id].stop()
        logging.info(f"Skipped current song in guild {ctx.guild.id}.")
        await play_next(ctx)

    @client.command(name="pause")
    async def pause(ctx):
        # Pause current playback
        if voice_clients[ctx.guild.id]:
            voice_clients[ctx.guild.id].pause()
            logging.info(f"Playback paused in guild {ctx.guild.id}.")

    @client.command(name="resume")
    async def resume(ctx):
        # Resume playback if it was paused
        if voice_clients[ctx.guild.id]:
            voice_clients[ctx.guild.id].resume()
            logging.info(f"Playback resumed in guild {ctx.guild.id}.")

    @client.command(name="stop")
    async def stop(ctx):
        # Stop playback and disconnect the bot from the voice channel
        if voice_clients[ctx.guild.id]:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            logging.info(f"Playback stopped and disconnected in guild {ctx.guild.id}.")

    @client.command(name="queue")
    async def queue(ctx, url):
        # Add a single song to the queue directly
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")
        logging.info(f"Added URL to queue for guild {ctx.guild.id}: {url}")
