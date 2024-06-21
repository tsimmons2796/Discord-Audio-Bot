import logging
from discord.ext import commands
from discord import Attachment, FFmpegPCMAudio, Interaction, PCMVolumeTransformer, app_commands, Guild, User, Embed, ButtonStyle, File, interactions, Intents, utils
from queue_manager import QueueEntry, queue_manager
from playback import PlaybackManager
from utils import download_file, extract_mp3_metadata
from views import ButtonView
import random
import re
import asyncio
from typing import Optional
import threading
import speech_recognition as sr
from youtubesearchpython import VideosSearch
import yt_dlp

logging.basicConfig(level=logging.DEBUG, filename='commands.log', format='%(asctime)s:%(levelname)s:%(message)s')

playback_manager = PlaybackManager(queue_manager)
recognizer = sr.Recognizer()

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.debug("Initializing MusicCommands Cog")

    @app_commands.command(name='play_next_in_queue', description='Move a specified track to the second position in the queue.')
    async def play_next(self, interaction: Interaction, youtube_url: str = None, youtube_title: str = None, mp3_file: Optional[Attachment] = None):
        await interaction.response.defer()  # Defer the interaction response
        logging.debug(f"Play next command executed for youtube_url: {youtube_url}, youtube_title: {youtube_title}, mp3_file: {mp3_file}")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)

        if youtube_url:
            if "list=" in youtube_url:
                playlist_length = await playback_manager.process_play_command(interaction, youtube_url, queue_manager, QueueEntry)
                for index in range(1, playlist_length + 1):
                    video_info = await playback_manager.fetch_info(youtube_url, index=index)
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
                            queue.insert(index, entry)
                            await interaction.followup.send(f"Added to queue: {entry.title} at position {index + 1}")
                            queue_manager.save_queues()
                            if not interaction.guild.voice_client.is_playing():
                                await playback_manager.play_audio(interaction, entry)
                    else:
                        await interaction.followup.send(f"Failed to retrieve video at index {index}")
                        break
            else:
                entry = await playback_manager.process_single_video_or_mp3(youtube_url, interaction, QueueEntry)
                if entry:
                    queue.insert(1, entry)
                    await interaction.followup.send(f"'{entry.title}' added to the queue at position 2.")
                    if not interaction.guild.voice_client.is_playing():
                        await playback_manager.play_audio(interaction, entry)
            return

        if youtube_title:
            try:
                videos_search = VideosSearch(youtube_title, limit=1)
                search_result = videos_search.result()

                if not search_result or not search_result['result']:
                    await interaction.followup.send("No video found for the youtube_title.")
                    return

                video_info = search_result['result'][0]
                video_url = video_info['link']
                title = video_info['title']
                thumbnail = video_info['thumbnails'][0]['url']
                duration_str = video_info.get('duration', '0:00')

                duration_parts = list(map(int, duration_str.split(':')))
                if len(duration_parts) == 2:
                    duration = duration_parts[0] * 60 + duration_parts[1]
                else:
                    duration = duration_parts[0]

                ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'ignoreerrors': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.get_running_loop().run_in_executor(None, lambda: ydl.extract_info(video_url, download=False))
                    best_audio_url = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), video_url)

                entry = QueueEntry(
                    video_url=video_url,
                    best_audio_url=best_audio_url,
                    title=title,
                    is_playlist=False,
                    thumbnail=thumbnail,
                    duration=duration
                )

                queue.insert(1, entry)
                queue_manager.save_queues()
                await interaction.followup.send(f"'{entry.title}' added to the queue at position 2.")
                if not interaction.guild.voice_client.is_playing():
                    await playback_manager.play_audio(interaction, entry)

            except Exception as e:
                logging.error(f"Error in play_next command: {e}")
                await interaction.followup.send("An error occurred while searching for the video.")
            return

        if mp3_file:
            file_path = await download_file(mp3_file.url, 'downloaded-mp3s')
            if file_path:
                metadata = extract_mp3_metadata(file_path)
                entry = QueueEntry(
                    video_url=mp3_file.url,
                    best_audio_url=file_path,
                    title=metadata['title'],
                    is_playlist=False,
                    playlist_index=None,
                    thumbnail=metadata['thumbnail'],
                    duration=metadata['duration']
                )
                queue.insert(1, entry)
                queue_manager.save_queues()
                await interaction.followup.send(f"Added {entry.title} to the queue at position 2.")
                if not interaction.guild.voice_client.is_playing():
                    await playback_manager.play_audio(interaction, entry)
            return

        await interaction.followup.send("Please provide a valid YouTube URL, YouTube title, or attach an MP3 file.")

    @app_commands.command(name='play', description='Play a YT URL, YT Title, or MP3 file if no audio is playing or add it to the end of the queue.')
    async def play(self, interaction: Interaction, youtube_url: str = None, youtube_title: str = None, mp3_file: Optional[Attachment] = None):
        await interaction.response.defer()  # Defer the interaction response

        voice_client = interaction.guild.voice_client
        if not voice_client and interaction.user.voice:
            voice_client = await interaction.user.voice.channel.connect()
        elif not voice_client:
            await interaction.followup.send("You are not connected to a voice channel.")
            return

        server_id = str(interaction.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        queue = queue_manager.get_queue(server_id)

        if mp3_file:
            file_path = await download_file(mp3_file.url, 'downloaded-mp3s')
            if file_path:
                metadata = extract_mp3_metadata(file_path)
                entry = QueueEntry(
                    video_url=mp3_file.url,
                    best_audio_url=file_path,
                    title=metadata['title'],
                    is_playlist=False,
                    playlist_index=None,
                    thumbnail=metadata['thumbnail'],
                    duration=metadata['duration']
                )
                queue_manager.add_to_queue(server_id, entry)
                if not interaction.guild.voice_client.is_playing():
                    await playback_manager.play_audio(interaction, entry)
                await interaction.followup.send(f"Added {entry.title} to the queue.")
            return

        if youtube_title:
            logging.debug(f"Search YouTube command executed for query: {youtube_title}")
            try:
                videos_search = VideosSearch(youtube_title, limit=1)
                search_result = videos_search.result()

                if not search_result or not search_result['result']:
                    await interaction.followup.send("No video found for the youtube_title.")
                    return

                video_info = search_result['result'][0]
                video_url = video_info['link']
                title = video_info['title']
                thumbnail = video_info['thumbnails'][0]['url']
                duration_str = video_info.get('duration', '0:00')

                duration_parts = list(map(int, duration_str.split(':')))
                if len(duration_parts) == 2:
                    duration = duration_parts[0] * 60 + duration_parts[1]
                else:
                    duration = duration_parts[0]

                ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'ignoreerrors': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.get_running_loop().run_in_executor(None, lambda: ydl.extract_info(video_url, download=False))
                    best_audio_url = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), video_url)

                entry = QueueEntry(
                    video_url=video_url,
                    best_audio_url=best_audio_url,
                    title=title,
                    is_playlist=False,
                    thumbnail=thumbnail,
                    duration=duration
                )

                if not queue_manager.currently_playing:
                    queue.insert(0, entry)
                    queue_manager.save_queues()
                    if not interaction.guild.voice_client:
                        if interaction.user.voice:
                            await interaction.user.voice.channel.connect()
                        else:
                            await interaction.followup.send("You are not connected to a voice channel.")
                            return
                    await playback_manager.play_audio(interaction, entry)
                else:
                    queue_manager.add_to_queue(server_id, entry)

                await interaction.followup.send(f"Added to queue: {title}")

            except Exception as e:
                logging.error(f"Error in search_youtube command: {e}")
                await interaction.followup.send("An error occurred while searching for the video.")
            return

        if youtube_url:
            if "list=" in youtube_url:
                await playback_manager.process_play_command(interaction, youtube_url, queue_manager, QueueEntry)
            else:
                entry = await playback_manager.process_single_video_or_mp3(youtube_url, interaction, QueueEntry)
                if entry:
                    if not queue_manager.currently_playing:
                        queue.insert(0, entry)
                        await playback_manager.play_audio(interaction, entry)
                    else:
                        queue_manager.add_to_queue(server_id, entry)
                    await interaction.followup.send(f"Added '{entry.title}' to the queue.")
            return

        await interaction.followup.send("Please provide a valid URL, YouTube video title, or attach an MP3 file.")

    @app_commands.command(name='previous', description='Play the last entry that was being played.')
    async def previous(self, interaction: Interaction):
        logging.debug("Previous command executed")
        server_id = str(interaction.guild.id)
        last_played = queue_manager.last_played_audio.get(server_id)
        if not last_played:
            await interaction.response.send_message("There was nothing played prior.")
            return

        queue = queue_manager.get_queue(server_id)
        entry = next((e for e in queue if e.title == last_played), None)

        if not entry:
            await interaction.response.send_message("No previously played track found.")
            return

        queue.remove(entry)
        queue.insert(1, entry)
        queue_manager.save_queues()
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await ButtonView.send_now_playing_for_buttons(interaction, entry)

    @app_commands.command(name='help', description='Show the help text.')
    async def help_command(self, interaction: Interaction):
        logging.debug("Help command executed")
        help_text = """
        Here are the commands and buttons you can use:

        **Commands:**

        **/clear_queue**
        - Clears the queue for today except the currently playing entry.

        **/list_queue**
        - Lists all entries currently in the queue.
        - Displays the current queue with each track's title and position.

        **/move_to_next [title]**
        - Moves a specified track to the second position in the queue by title.
        - If a title is provided and found in the queue, it will be moved to the second position.

        **/pause**
        - Pauses the currently playing track.

        **/play [URL or attachment]**
        - Plays audio from a YouTube URL, a YouTube title, or an attached MP3 file.
        - If a URL is provided, it can be a single video or a playlist. If it's a playlist, all videos will be added to the queue.
        - If a YouTube title is provided, the bot will search for the video and play the first result.
        - If an MP3 file is attached, it will be added to the queue and played if nothing is currently playing.

        **/play_next_in_queue [URL, YouTube title, or MP3 attachment]**
        - Adds a new entry to the second position in the queue.
        - If a URL is provided, the video or playlist will be added to the second position.
        - If a YouTube title is provided, the bot will search for the video and add the first result to the second position.
        - If an MP3 file is attached, it will be added to the second position in the queue.

        **/play_queue**
        - Starts playing the queue from the first track.

        **/previous**
        - Plays the last entry that was being played.

        **/remove_by_title [title]**
        - Removes a specific track by its title from the queue.
        - If the title is found in the queue, it will be removed.

        **/remove_queue [index]**
        - Removes a track from the queue by its index.
        - The index is the position in the queue, starting from 1.

        **/restart**
        - Restarts the currently playing track from the beginning.

        **/resume**
        - Resumes playback if it is paused.

        **/search_and_play_from_queue [title]**
        - Searches the current queue and plays the specified track.
        - Use this command to play a specific track from the queue immediately.

        **/shuffle**
        - Randomly shuffles the current queue and shows the new order.

        **/skip**
        - Skips the current track and plays the next one in the queue.
        - If there is no next track, the playback stops.

        **/stop**
        - Stops playback and disconnects the bot from the voice channel.

        **Buttons:**

        **💛 Favorited / ⭐ Favorite**
        - Toggles the favorite status of the current track.
        - Users can mark tracks as favorites, which will be displayed in the "Now Playing" embed.

        **⬇️ Move Down**
        - Moves the current track down one position in the queue.

        **⬇️⬇️ Move to Bottom**
        - Moves the current track to the bottom of the queue.

        **⬆️ Move Up**
        - Moves the current track up one position in the queue.

        **⬆️⬆️ Move to Top**
        - Moves the current track to the top of the queue.

        **📜 List Queue**
        - Lists all entries currently in the queue.
        - Displays the current queue with each track's title and position.

        **Lyrics**
        - Fetches and displays the lyrics for the current track.
        - The bot will search for the lyrics based on the current track's title and artist.

        **🔁 Loop**
        - Toggles looping of the current track.
        - If enabled, the current track will repeat after it finishes playing.
        - Continues looping the current track until the loop button is clicked again.

        **⏸️ Pause**
        - Pauses the currently playing track.

        **⏮️ Previous**
        - Plays the last entry that was being played.
        - Useful for returning to the previously played track.

        **🔄 Restart**
        - Restarts the currently playing track from the beginning.

        **⏭️ Skip**
        - Skips the current track and plays the next one in the queue.

        **⏹️ Stop**
        - Stops playback and disconnects the bot from the voice channel.

        **🔀 Shuffle**
        - Randomly shuffles the current queue and shows the new order.

        **❌ Remove**
        - Removes the current track from the queue.
        - If the removed track is currently playing, playback stops.

        **Type a command to execute it. For example: `/play https://youtube.com/watch?v=example`**

        **Always taking suggestions for the live service of Radio-Bot**
        """
        max_length = 2000
        pattern = re.compile(r"(\*\*.+?\*\*[\s\S]*?(?=\n\s*\*\*|$))")

        matches = pattern.findall(help_text)
        chunks = []
        current_chunk = ""

        for match in matches:
            if len(current_chunk) + len(match) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += match + "\n"
        
        if current_chunk:
            chunks.append(current_chunk)

        for i, chunk in enumerate(chunks):
            if "**Buttons:**" in chunk:
                button_section_start_index = chunk.index("**Buttons:**")
                before_buttons = chunk[:button_section_start_index]
                buttons_and_after = chunk[button_section_start_index:]
                if len(before_buttons) + len(buttons_and_after.split("\n", 2)[0]) > max_length:
                    chunks[i] = before_buttons
                    chunks.insert(i + 1, buttons_and_after)
                else:
                    chunks[i] = before_buttons + buttons_and_after
                break

        first_message_sent = False
        for chunk in chunks:
            if not first_message_sent:
                await interaction.response.send_message(chunk)
                first_message_sent = True
            else:
                await interaction.followup.send(chunk)

    @app_commands.command(name='remove_by_title', description='Remove a track from the queue by title.')
    async def remove_by_title(self, interaction: Interaction, title: str):
        logging.debug(f"Remove by title command executed for title: {title}")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return

        original_length = len(queue)
        queue = [entry for entry in queue if entry.title != title]
        if len(queue) == original_length:
            await interaction.response.send_message(f"No track found with title '{title}'.")
        else:
            queue_manager.queues[server_id] = queue
            queue_manager.save_queues()
            await interaction.response.send_message(f"Removed '{title}' from the queue.")

    @app_commands.command(name='shuffle', description='Shuffle the current queue.')
    async def shuffle(self, interaction: Interaction):
        logging.debug("Shuffle command executed")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
            return
        first_entry_before_shuffle = queue_manager.currently_playing

        queue_manager.has_been_shuffled = True
        random.shuffle(queue)
        for entry in queue:
            entry.has_been_arranged = False
        queue_manager.queues[server_id] = queue
        queue_manager.save_queues()

        titles = [entry.title for entry in queue]
        response = "Queue after shuffle:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

        max_length = 2000  # Discord message character limit
        chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

        for chunk in chunks:
            await interaction.channel.send(chunk)
        
        if first_entry_before_shuffle or any(vc.is_paused() for vc in interaction.guild.voice_clients):
            await ButtonView.send_now_playing_for_buttons(interaction, first_entry_before_shuffle)

    @app_commands.command(name='play_queue', description='Play the current queue.')
    async def play_queue(self, interaction: Interaction):
        logging.debug("Play queue command executed")
        
        await interaction.response.defer()  # Defer the response to give more time for processing

        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.followup.send("Queue is empty, please add some tracks first.")
            return

        entry = queue[0] if queue else None
        if entry:
            if not interaction.guild.voice_client:
                if interaction.user.voice:
                    await interaction.user.voice.channel.connect()
                else:
                    await interaction.followup.send("You are not connected to a voice channel.")
                    return

            await playback_manager.play_audio(interaction, entry)
        else:
            await interaction.followup.send("Queue is empty.")

    @app_commands.command(name='list_queue', description='List all entries in the current queue.')
    async def list_queue(self, interaction: Interaction):
        logging.debug("List queue command executed")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.response.send_message("The queue is currently empty.")
        else:
            titles = [entry.title for entry in queue]
            response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))

            max_length = 2000  # Discord message character limit
            chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]

            for chunk in chunks:
                await interaction.channel.send(chunk)
            
            if queue_manager.currently_playing:
                await ButtonView.send_now_playing_for_buttons(interaction, queue_manager.currently_playing)

    @app_commands.command(name='remove_queue', description='Remove a track from the queue by index.')
    async def remove_queue(self, interaction: Interaction, index: int):
        logging.debug(f"Remove queue command executed for index: {index}")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        adjusted_index = index - 1

        if 0 <= adjusted_index < len(queue):
            removed_entry = queue.pop(adjusted_index)
            queue_manager.save_queues()
            await interaction.response.send_message(f"Removed '{removed_entry.title}' from the queue.")
        else:
            await interaction.response.send_message("Invalid index. Please provide a valid index of the song to remove.")

    @app_commands.command(name='skip', description='Skip the current track.')
    async def skip(self, interaction: Interaction):
        logging.debug("Skip command executed")
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)
        if not queue:
            await interaction.response.send_message("Queue is empty.")
            return

        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            current_entry = queue_manager.currently_playing
            if current_entry:
                if current_entry.has_been_arranged and current_entry.has_been_played_after_arranged:
                    current_entry.has_been_arranged = False
                    current_entry.has_been_played_after_arranged = False
                elif current_entry.has_been_arranged and not current_entry.has_been_played_after_arranged:
                    current_entry.has_been_played_after_arranged = True
                    queue.remove(current_entry)
                    queue.append(current_entry)
                    queue_manager.save_queues()
                elif not queue_manager.has_been_shuffled:
                    queue.remove(current_entry)
                    queue.append(current_entry)
                    queue_manager.save_queues()
                interaction.guild.voice_client.stop()
                await asyncio.sleep(0.5)

    @app_commands.command(name='pause', description='Pause the currently playing track.')
    async def pause(self, interaction: Interaction):
        logging.debug("Pause command executed")
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            message = await interaction.original_message()
            view = message.components[0].view
            view.paused = True
            view.update_buttons()
            await message.edit(view=view)
            await interaction.response.send_message('Playback paused.')
            logging.info("Playback paused.")
            print("Playback paused.")

    @app_commands.command(name='resume', description='Resume playback if it is paused.')
    async def resume(self, interaction: Interaction):
        logging.debug("Resume command executed")
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            message = await interaction.original_message()
            view = message.components[0].view
            view.paused = False
            view.update_buttons()
            await message.edit(view=view)
            await interaction.response.send_message('Playback resumed.')
            logging.info("Playback resumed.")
            print("Playback resumed.")

    @app_commands.command(name='stop', description='Stop playback and disconnect the bot from the voice channel.')
    async def stop(self, interaction: Interaction):
        logging.debug("Stop command executed")
        queue_manager.currently_playing = None
        queue_manager.stop_is_triggered = True
        if interaction.guild.voice_client:
            try:
                interaction.guild.voice_client.stop()
            except Exception as e:
                logging.error(f"Error stopping the voice client: {e}")
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message('Playback stopped and disconnected.', ephemeral=True)

    @app_commands.command(name='restart', description='Restart the currently playing track from the beginning.')
    async def restart(self, interaction: Interaction):
        logging.debug("Restart command executed")
        if not queue_manager.currently_playing:
            await interaction.response.send_message("No track is currently playing.")
            return

        current_entry = queue_manager.currently_playing
        queue_manager.is_restarting = True

        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await asyncio.sleep(0.5)
            await playback_manager.play_audio(interaction, current_entry)
            
    @commands.command(name='mp3_list_next')
    async def mp3_list_next(self, ctx):
        logging.debug("mp3_list_next command invoked")
        print("mp3_list_next command invoked")

        voice_client = utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not voice_client and ctx.author.voice:
            logging.debug("Connecting to voice channel")
            print("Connecting to voice channel")
            voice_client = await ctx.author.voice.channel.connect()
        elif not voice_client:
            logging.warning("User is not connected to a voice channel")
            print("User is not connected to a voice channel")
            await ctx.send("You are not connected to a voice channel.")
            return

        server_id = str(ctx.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        logging.debug(f"Queue exists ensured for server {server_id}")
        print(f"Queue exists ensured for server {server_id}")

        if ctx.message.attachments:
            logging.debug("Processing attachments")
            print("Processing attachments")
            current_index = 1
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith('.mp3'):
                    logging.info(f"Downloading attachment: {attachment.filename}")
                    print(f"Downloading attachment: {attachment.filename}")
                    file_path = await download_file(attachment.url, 'downloaded-mp3s')
                    if file_path:
                        metadata = extract_mp3_metadata(file_path)
                        entry = QueueEntry(
                            video_url=attachment.url,
                            best_audio_url=file_path,
                            title=metadata['title'],
                            is_playlist=False,
                            playlist_index=None,
                            thumbnail=metadata['thumbnail'],
                            duration=metadata['duration']
                        )
                        queue = queue_manager.get_queue(server_id)
                        queue.insert(current_index, entry)
                        current_index += 1
                        queue_manager.save_queues()
                        logging.info(f"Added '{entry.title}' to queue at position {current_index}")
                        print(f"Added '{entry.title}' to queue at position {current_index}")
                        await ctx.send(f"'{entry.title}' added to the queue at position {current_index}.")
                        if not voice_client.is_playing() and current_index == 2:
                            await playback_manager.play_audio(ctx, entry)
            return
        else:
            logging.warning("No valid URL or attachment provided")
            print("No valid URL or attachment provided")
            await ctx.send("Please provide a valid URL or attach an MP3 file.")

    @commands.command(name='mp3_list')
    async def mp3_list(self, ctx, url: str = None):
        logging.debug("mp3_list command invoked")
        print("mp3_list command invoked")

        voice_client = utils.get(ctx.bot.voice_clients, guild=ctx.guild)
        if not voice_client and ctx.author.voice:
            logging.debug("Connecting to voice channel")
            print("Connecting to voice channel")
            voice_client = await ctx.author.voice.channel.connect()
        elif not voice_client:
            logging.warning("User is not connected to a voice channel")
            print("User is not connected to a voice channel")
            await ctx.send("You are not connected to a voice channel.")
            return

        server_id = str(ctx.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        logging.debug(f"Queue exists ensured for server {server_id}")
        print(f"Queue exists ensured for server {server_id}")

        if ctx.message.attachments:
            logging.debug("Processing attachments")
            print("Processing attachments")
            first_entry_processed = False
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith('.mp3'):
                    logging.info(f"Downloading attachment: {attachment.filename}")
                    print(f"Downloading attachment: {attachment.filename}")
                    file_path = await download_file(attachment.url, 'downloaded-mp3s')
                    if file_path:
                        metadata = extract_mp3_metadata(file_path)
                        entry = QueueEntry(
                            video_url=attachment.url,
                            best_audio_url=file_path,
                            title=metadata['title'],
                            is_playlist=False,
                            playlist_index=None,
                            thumbnail=metadata['thumbnail'],
                            duration=metadata['duration']
                        )
                        queue_manager.add_to_queue(server_id, entry)
                        logging.info(f"Added '{entry.title}' to queue")
                        print(f"Added '{entry.title}' to queue")
                        await ctx.send(f"'{entry.title}' added to the queue.")
                        if not voice_client.is_playing() and not first_entry_processed:
                            await playback_manager.play_audio(ctx, entry)
                            first_entry_processed = True
            return
        else:
            logging.warning("No valid URL or attachment provided")
            print("No valid URL or attachment provided")
            await ctx.send("Please provide a valid URL or attach an MP3 file.")

    @commands.command(name='listen')
    async def listen(self, ctx):
        # Check if bot is connected to a voice channel
        if ctx.author.voice is None:
            await ctx.send("You are not connected to a voice channel.")
            return

        voice_channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await voice_channel.connect()
        elif ctx.voice_client.channel != voice_channel:
            await ctx.voice_client.move_to(voice_channel)

        await ctx.send("Listening...")

        def listen_in_background():
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                while True:
                    try:
                        audio = recognizer.listen(source)
                        text = recognizer.recognize_google(audio)
                        print(text)
                        logging.info(text)
                        # Process the recognized text for commands
                        logging.info(f"Recognized command: {text}")
                        self.process_voice_command(text, ctx)
                    except sr.UnknownValueError:
                        print("Google Speech Recognition could not understand audio")
                        logging.error("Google Speech Recognition could not understand audio")
                    except sr.RequestError as e:
                        print(f"Could not request results from Google Speech Recognition service; {e}")
                        logging.error(f"Could not request results from Google Speech Recognition service; {e}")

        threading.Thread(target=listen_in_background, daemon=True).start()

    def process_voice_command(self, text, ctx):
        if "hey cuba" in text.lower() and "thanks" in text.lower():
            command = text.lower().split("hey cuba", 1)[1].split("thanks", 1)[0].strip()
            print(f"Recognized command: {command}")
            logging.info(f"Processing voice command: {command}")
            
            command_mappings = {
                'play playlist': self.play_queue,
                'pause': self.pause,
                'resume': self.resume,
                'skip': self.skip,
                'restart': self.restart,
                'loop': self.loop,
                'display playlist': self.list_queue,
                'shuffle playlist': self.shuffle
            }
            
            for key, func in command_mappings.items():
                if key in command:
                    self.bot.loop.create_task(func(ctx))
                    break

    @app_commands.autocomplete(title="title_autocomplete")
    async def title_autocomplete(self, interaction: Interaction, current: str):
        server_id = str(interaction.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        queue = queue_manager.get_queue(server_id)
        titles = [entry.title for entry in queue if current.lower() in entry.title.lower()]
        return [app_commands.Choice(name=title, value=title) for title in titles[:25]]

    @app_commands.command(name="search_and_play_from_queue", description="Search the current queue and play the specified track.")
    @app_commands.autocomplete(title=title_autocomplete)
    async def search_and_play_from_queue(self, interaction: Interaction, title: str):
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)

        entry_index = next((i for i, entry in enumerate(queue) if entry.title == title), None)
        if entry_index is None:
            await interaction.response.send_message("No match found in the current queue.")
            return

        entry = queue.pop(entry_index)
        queue.insert(0, entry)
        queue_manager.save_queues()

        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await asyncio.sleep(1)

        if not voice_client:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()

        await playback_manager.play_audio(interaction, entry)

    @app_commands.command(name='move_to_next', description="Move the specified track in the queue to the second position.")
    @app_commands.autocomplete(title=title_autocomplete)
    async def queue_up_next(self, interaction: Interaction, title: str):
        server_id = str(interaction.guild.id)
        queue = queue_manager.get_queue(server_id)

        entry_index = next((i for i, entry in enumerate(queue) if entry.title == title), None)
        if entry_index is None:
            await interaction.response.send_message("No match found in the current queue.")
            return

        entry = queue.pop(entry_index)
        queue.insert(1, entry)
        queue_manager.save_queues()
        
        await interaction.response.send_message(f"Moved '{title}' to the second position in the queue.")
    
    @app_commands.command(name='clear_queue', description='Clear the queue except the currently playing entry.')
    async def clear_queue(self, interaction: Interaction):
        logging.debug("Clear queue command executed")
        server_id = str(interaction.guild.id)
        current_entry = queue_manager.currently_playing
        if server_id in queue_manager.queues:
            if current_entry and current_entry in queue_manager.queues[server_id]:
                queue_manager.queues[server_id] = [current_entry]
            else:
                queue_manager.queues[server_id] = []
            queue_manager.save_queues()
            await interaction.response.send_message(f"The queue for server '{interaction.guild.name}' has been cleared, except the currently playing entry.")
        else:
            await interaction.response.send_message(f"There is no queue for server '{interaction.guild.name}' to clear.")

async def setup_commands(bot):
    await bot.add_cog(MusicCommands(bot))
