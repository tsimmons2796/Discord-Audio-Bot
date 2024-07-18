import logging
import asyncio
import random
import yt_dlp
from discord import Attachment, Interaction, utils, Embed
from youtubesearchpython import VideosSearch
from queue_manager import QueueEntry, queue_manager
from playback import PlaybackManager
from utils import download_file, extract_mp3_metadata, sanitize_title, delete_file
from button_view import ButtonView
from typing import Optional

logging.basicConfig(level=logging.DEBUG, filename='commands.log', format='%(asctime)s:%(levelname)s:%(message)s')

playback_manager = PlaybackManager(queue_manager)

async def process_play_next(interaction: Interaction, youtube_url: str, youtube_title: str, mp3_file: Optional[Attachment]):
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)

    if youtube_url:
        if "list=" in youtube_url:
            await playback_manager.process_play_command(interaction, youtube_url)
        else:
            entry = await playback_manager.process_single_video_or_mp3(youtube_url, interaction)
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

async def process_play(interaction: Interaction, youtube_url: str, youtube_title: str, mp3_file: Optional[Attachment]):
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
            await playback_manager.process_play_command(interaction, youtube_url)
        else:
            entry = await playback_manager.process_single_video_or_mp3(youtube_url, interaction)
            if entry:
                if not queue_manager.currently_playing:
                    queue.insert(0, entry)
                    await playback_manager.play_audio(interaction, entry)
                else:
                    queue_manager.add_to_queue(server_id, entry)
                await interaction.followup.send(f"Added '{entry.title}' to the queue.")
        return

    await interaction.followup.send("Please provide a valid URL, YouTube video title, or attach an MP3 file.")

async def process_previous(interaction: Interaction):
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

async def process_remove_by_title(interaction: Interaction, title: str):
    logging.debug(f"Remove by title command executed for title: {title}")
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    if not queue:
        await interaction.response.send_message("The queue is currently empty.")
        return

    original_length = len(queue)
    queue = [entry for entry in queue if entry.title != title]
    removed_entries = [entry for entry in queue_manager.queues[server_id] if entry.title == title]
    if len(queue) == original_length:
        await interaction.response.send_message(f"No track found with title '{title}'.")
    else:
        queue_manager.queues[server_id] = queue
        queue_manager.save_queues()
        for entry in removed_entries:
            if entry.best_audio_url.startswith("downloaded-mp3s/"):
                await delete_file(entry.best_audio_url)
        await interaction.response.send_message(f"Removed '{title}' from the queue.")

async def process_shuffle(interaction: Interaction):
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

async def process_play_queue(interaction: Interaction):
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

async def process_list_queue(interaction: Interaction):
    logging.debug("List queue command executed")
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    
    if not queue:
        await interaction.response.send_message("The queue is currently empty.")
        return
    
    def format_duration(seconds):
        mins, secs = divmod(seconds, 60)
        return f"{mins}:{secs:02d}"
    
    def create_embed(title, description, fields):
        embed = Embed(title=title, description=description)
        for field in fields:
            embed.add_field(name=field["name"], value=field["description"], inline=False)
        return embed

    fields = []
    for idx, entry in enumerate(queue):
        field_name = f"{idx + 1}. {entry.title}"
        if "youtube.com" in entry.video_url or "youtu.be" in entry.video_url:
            field_value = (
                f"**URL:** [Link]({entry.video_url})\n"
                f"**Duration:** {format_duration(entry.duration)}\n"
                f"**Favorited by:** {', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else 'No one'}"
            )
        else:
            field_value = (
                f"**Duration:** {format_duration(entry.duration)}\n"
                f"**Favorited by:** {', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else 'No one'}"
            )
        fields.append({"name": field_name, "description": field_value})
    
    max_fields_per_embed = 25
    queue_embeds = []
    for i in range(0, len(fields), max_fields_per_embed):
        embed_fields = fields[i:i + max_fields_per_embed]
        embed = create_embed("Current Queue", f"Listing entries {i + 1} - {i + len(embed_fields)}", embed_fields)
        queue_embeds.append(embed)

    # Send the first embed with the interaction response
    await interaction.response.send_message(embed=queue_embeds[0])

    # Send the rest of the embeds as follow-up messages
    for embed in queue_embeds[1:]:
        await interaction.followup.send(embed=embed)
    
    if queue_manager.currently_playing:
        await ButtonView.send_now_playing_for_buttons(interaction, queue_manager.currently_playing)

async def process_remove_queue(interaction: Interaction, index: int):
    logging.debug(f"Remove queue command executed for index: {index}")
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    adjusted_index = index - 1

    if 0 <= adjusted_index < len(queue):
        removed_entry = queue.pop(adjusted_index)
        queue_manager.save_queues()
        if removed_entry.best_audio_url.startswith("downloaded-mp3s/"):
            await delete_file(removed_entry.best_audio_url)
        await interaction.response.send_message(f"Removed '{removed_entry.title}' from the queue.")
    else:
        await interaction.response.send_message("Invalid index. Please provide a valid index of the song to remove.")

async def process_skip(interaction: Interaction):
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

async def process_pause(interaction: Interaction):
    logging.debug("Pause command executed")
    server_id = str(interaction.guild.id)
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        queue_manager.is_paused = True
        message = await interaction.original_message()
        view = message.components[0].view
        view.paused = True
        view.update_buttons()
        await message.edit(view=view)
        await interaction.response.send_message('Playback paused.')
        logging.info("Playback paused.")

async def process_resume(interaction: Interaction):
    logging.debug("Resume command executed")
    server_id = str(interaction.guild.id)
    if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        queue_manager.is_paused = False
        message = await interaction.original_message()
        view = message.components[0].view
        view.paused = False
        view.update_buttons()
        await message.edit(view=view)
        await interaction.response.send_message('Playback resumed.')
        logging.info("Playback resumed.")

async def process_stop(interaction: Interaction):
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

async def process_restart(interaction: Interaction):
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

async def process_mp3_list_next(ctx):
    logging.debug("mp3_list_next command invoked")

    voice_client = utils.get(ctx.bot.voice_clients, guild=ctx.guild)
    if not voice_client and ctx.author.voice:
        logging.debug("Connecting to voice channel")
        voice_client = await ctx.author.voice.channel.connect()
    elif not voice_client:
        logging.warning("User is not connected to a voice channel")
        await ctx.send("You are not connected to a voice channel.")
        return

    server_id = str(ctx.guild.id)
    queue_manager.ensure_queue_exists(server_id)
    logging.debug(f"Queue exists ensured for server {server_id}")

    if ctx.message.attachments:
        logging.debug("Processing attachments")
        current_index = 1
        for attachment in ctx.message.attachments:
            if attachment.filename.lower().endswith('.mp3'):
                logging.info(f"Downloading attachment: {attachment.filename}")
                file_path = await download_file(attachment.url, 'downloaded-mp3s')
                if file_path:
                    metadata = extract_mp3_metadata(file_path)
                    sanitized_title = sanitize_title(metadata['title'])
                    entry = QueueEntry(
                        video_url=attachment.url,
                        best_audio_url=file_path,
                        title=sanitized_title,
                        is_playlist=False,
                        thumbnail=metadata['thumbnail'],
                        duration=metadata['duration']
                    )
                    queue = queue_manager.get_queue(server_id)
                    if not any(e.title == entry.title for e in queue):  # Check for duplicates
                        queue.insert(current_index, entry)
                        current_index += 1
                        queue_manager.save_queues()
                        logging.info(f"Added '{entry.title}' to queue at position {current_index}")
                        await ctx.send(f"'{entry.title}' added to the queue at position {current_index}.")
                        if not voice_client.is_playing() and current_index == 2:
                            await playback_manager.play_audio(ctx, entry)
        return
    else:
        logging.warning("No valid URL or attachment provided")
        await ctx.send("Please provide a valid URL or attach an MP3 file.")

async def process_mp3_list(ctx):
    logging.debug("mp3_list command invoked")

    voice_client = utils.get(ctx.bot.voice_clients, guild=ctx.guild)
    if not voice_client and ctx.author.voice:
        logging.debug("Connecting to voice channel")
        voice_client = await ctx.author.voice.channel.connect()
    elif not voice_client:
        logging.warning("User is not connected to a voice channel")
        await ctx.send("You are not connected to a voice channel.")
        return

    server_id = str(ctx.guild.id)
    queue_manager.ensure_queue_exists(server_id)
    logging.debug(f"Queue exists ensured for server {server_id}")

    if ctx.message.attachments:
        logging.debug("Processing attachments")
        first_entry_processed = False
        for attachment in ctx.message.attachments:
            if attachment.filename.lower().endswith('.mp3'):
                logging.info(f"Downloading attachment: {attachment.filename}")
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
                    await ctx.send(f"'{entry.title}' added to the queue.")
                    if not voice_client.is_playing() and not first_entry_processed:
                        await playback_manager.play_audio(ctx, entry)
                        first_entry_processed = True
        return
    else:
        logging.warning("No valid URL or attachment provided")
        await ctx.send("Please provide a valid URL or attach an MP3 file.")

async def process_clear_queue(interaction: Interaction):
    logging.debug("Clear queue command executed")
    server_id = str(interaction.guild.id)
    current_entry = queue_manager.currently_playing
    if server_id in queue_manager.queues:
        removed_entries = queue_manager.queues[server_id]
        if current_entry and current_entry in removed_entries:
            queue_manager.queues[server_id] = [current_entry]
        else:
            queue_manager.queues[server_id] = []
        queue_manager.save_queues()
        for entry in removed_entries:
            if entry.best_audio_url.startswith("downloaded-mp3s/"):
                await delete_file(entry.best_audio_url)
        await interaction.response.send_message(f"The queue for server '{interaction.guild.name}' has been cleared, except the currently playing entry.")
    else:
        await interaction.response.send_message(f"There is no queue for server '{interaction.guild.name}' to clear.")

async def process_move_to_next(interaction: Interaction, title: str):
    logging.debug(f"Move to next command executed for title: {title}")
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

async def process_search_and_play_from_queue(interaction: Interaction, title: str):
    logging.debug("Search and play from queue command executed")
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

async def process_help(interaction: Interaction):
    commands_info = [
        {"name": "/play_next_in_queue", "description": "Move a specified track to the second position in the queue."},
        {"name": "/play", "description": "Play a YouTube URL, YouTube Title, or MP3 file if no audio is playing or add it to the end of the queue."},
        {"name": "/previous", "description": "Play the last entry that was being played."},
        {"name": "/remove_by_title", "description": "Remove a track from the queue by title."},
        {"name": "/shuffle", "description": "Shuffle the current queue."},
        {"name": "/play_queue", "description": "Play the current queue."},
        {"name": "/list_queue", "description": "List all entries in the current queue."},
        {"name": "/remove_queue", "description": "Remove a track from the queue by index."},
        {"name": "/skip", "description": "Skip the current track."},
        {"name": "/pause", "description": "Pause the currently playing track."},
        {"name": "/resume", "description": "Resume playback if it is paused."},
        {"name": "/stop", "description": "Stop playback and disconnect the bot from the voice channel."},
        {"name": "/restart", "description": "Restart the currently playing track from the beginning."},
        {"name": "/clear_queue", "description": "Clear the queue except the currently playing entry."},
        {"name": "/move_to_next", "description": "Move the specified track in the queue to the second position."},
        {"name": "/search_and_play_from_queue", "description": "Search the current queue and play the specified track."},
        {"name": "/help", "description": "Show the help text."},
        {"name": ".mp3_list_next", "description": "List MP3 files and play the next one in the list."},
        {"name": ".mp3_list", "description": "List all available MP3 files."}
    ]

    buttons_info = [
        {"label": "⏸️ Pause", "description": "Pause the current playback."},
        {"label": "▶️ Resume", "description": "Resume the paused playback."},
        {"label": "⏹️ Stop", "description": "Stop playback and disconnect the bot."},
        {"label": "⏭️ Skip", "description": "Skip the current track."},
        {"label": "🔄 Restart", "description": "Restart the current track."},
        {"label": "🔀 Shuffle", "description": "Shuffle the current queue."},
        {"label": "📜 List Queue", "description": "List all entries in the current queue."},
        {"label": "❌ Remove", "description": "Remove the current track from the queue."},
        {"label": "⏮️ Previous", "description": "Play the previously played track."},
        {"label": "🔁 Loop", "description": "Toggle looping of the current track."},
        {"label": "⬆️ Move Up", "description": "Move the current track up in the queue."},
        {"label": "⬇️ Move Down", "description": "Move the current track down in the queue."},
        {"label": "⬆️⬆️ Move to Top", "description": "Move the current track to the top of the queue."},
        {"label": "⬇️⬇️ Move to Bottom", "description": "Move the current track to the bottom of the queue."},
        {"label": "⭐ Favorite", "description": "Add the current track to favorites."},
        {"label": "💛 Favorited", "description": "The track is already favorited."},
        {"label": "Lyrics", "description": "Show the lyrics for the current track."}
    ]

    def create_embed(title, description, fields):
        embed = Embed(title=title, description=description)
        for field in fields:
            embed.add_field(name=field["name"], value=field["description"], inline=False)
        return embed

    # Combine command and button info into one list
    combined_info = [{"name": cmd["name"], "description": cmd["description"]} for cmd in commands_info]
    combined_info += [{"name": btn["label"], "description": btn["description"]} for btn in buttons_info]

    # Create multiple embeds if needed
    max_fields_per_embed = 25
    help_embeds = []
    for i in range(0, len(combined_info), max_fields_per_embed):
        help_embeds.append(create_embed("Help - Music Commands", "List of available commands and their descriptions.", combined_info[i:i + max_fields_per_embed]))

    for embed in help_embeds:
        await interaction.response.send_message(embed=embed)
