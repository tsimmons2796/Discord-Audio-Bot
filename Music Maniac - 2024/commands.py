import discord
import logging
import asyncio
import yt_dlp

voice_clients = {}
queues = {}
yt_dl_options = {"format": "bestaudio/best"}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)
ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn -filter:a "volume=0.25"'}

def setup_commands(client):
    async def play_next(ctx):
        if queues[ctx.guild.id]:
            link = queues[ctx.guild.id].pop(0)
            logging.info(f"Playing next in queue for guild {ctx.guild.id}: {link}")
            await play(ctx, link)
        else:
            # Wait for a while before leaving the channel, adjust 'wait_seconds' as needed
            wait_seconds = 30
            await asyncio.sleep(wait_seconds)
            if not queues[ctx.guild.id]:  # Check again to make sure no new songs have been added
                if ctx.guild.id in voice_clients:
                    if voice_clients[ctx.guild.id].is_connected():
                        await voice_clients[ctx.guild.id].disconnect()
                        del voice_clients[ctx.guild.id]
                        logging.info(f"Disconnected from voice channel in guild {ctx.guild.id} due to empty queue.")
    @client.command(name="play")
    async def play(ctx, link):
        if ctx.author.voice is None:
            await ctx.send("Get in a voice channel first...")
            logging.warning("Attempt to play music without being in a voice channel.")
            return
        
        # Check if the bot is already connected to the voice channel
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
            logging.info("Bot is already connected to the voice channel.")
            voice_client = voice_clients[ctx.guild.id]
        else:
            try:
                voice_client = await ctx.author.voice.channel.connect()
                voice_clients[ctx.guild.id] = voice_client
                logging.info(f"Connected to voice channel in guild {ctx.guild.id}")
            except Exception as e:
                logging.error(f"Error connecting to voice channel: {e}")
                return

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
            song = data['url']
            logging.info(f"Extracted URL for playback: {song}")
        except Exception as e:
            logging.error(f"Failed to extract video data: {e}")
            return

        try:
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
            logging.info("Playback started.")
        except Exception as e:
            logging.error(f"Failed to start FFmpeg player: {e}")

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
        voice_clients[ctx.guild.id].stop()
        logging.info(f"Skipped current song in guild {ctx.guild.id}.")
        await play_next(ctx)

    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
            logging.info(f"Playback paused in guild {ctx.guild.id}.")
        except Exception as e:
            logging.error(f"Error pausing: {e}")

    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
            logging.info(f"Playback resumed in guild {ctx.guild.id}.")
        except Exception as e:
            logging.error(f"Error resuming: {e}")

    @client.command(name="stop")
    async def stop(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
            logging.info(f"Playback stopped and disconnected in guild {ctx.guild.id}.")
        except Exception as e:
            logging.error(f"Error stopping playback: {e}")

    @client.command(name="queue")
    async def queue(ctx, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")
        logging.info(f"Added URL to queue for guild {ctx.guild.id}: {url}")