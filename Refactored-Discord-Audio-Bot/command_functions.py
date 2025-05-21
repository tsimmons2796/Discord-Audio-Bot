import logging
import re
import asyncio
import random
import yt_dlp
import os
from discord import Attachment, Interaction, utils, Embed
from queue_manager import QueueEntry, queue_manager
from playback import PlaybackManager
from utils import download_file, extract_mp3_metadata, sanitize_title, delete_file
from button_view import ButtonView
from typing import Optional, List, Dict, Tuple, Set
from config import LASTFM_API_KEY
from urllib.parse import quote_plus
import aiohttp

logging.basicConfig(level=logging.DEBUG, filename='commands.log', format='%(asctime)s:%(levelname)s:%(message)s')

playback_manager = PlaybackManager(queue_manager)

async def process_remove_duplicates(interaction: Interaction):
    logging.debug("Remove duplicates command executed")
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)

    if not queue:
        await interaction.response.send_message("The queue is currently empty.")
        return

    seen_titles = set()
    unique_queue = []
    removed_titles = []

    for entry in queue:
        if entry.title.lower() not in seen_titles:
            unique_queue.append(entry)
            seen_titles.add(entry.title.lower())
        else:
            removed_titles.append(entry.title)

    queue_manager.queues[server_id] = unique_queue
    queue_manager.save_queues()

    if removed_titles:
        await interaction.response.send_message(f"Removed {len(removed_titles)} duplicate entries from the queue.")
    else:
        await interaction.response.send_message("No duplicates found in the queue.")


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
            # Check if a track with this title is already in the queue
            queue_titles = set(entry.title.lower() for entry in queue)
            
            # Try to find a non-duplicate YouTube result
            entry = await find_non_duplicate_youtube_result(youtube_title, queue_titles, interaction)
            
            if entry:
                queue.insert(1, entry)
                queue_manager.save_queues()
                await interaction.followup.send(f"'{entry.title}' added to the queue at position 2.")
                if not interaction.guild.voice_client.is_playing():
                    await playback_manager.play_audio(interaction, entry)
            else:
                await interaction.followup.send("Could not find a unique track that isn't already in the queue.")

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

async def process_play(interaction: Interaction, youtube_url: str = None, youtube_title: str = None, mp3_file: Optional[Attachment] = None):
    """
    Process a play command to add a track to the queue and start playback if nothing is playing.
    
    Args:
        interaction: The Discord interaction object
        youtube_url: Optional YouTube URL to play
        youtube_title: Optional YouTube title to search for
        mp3_file: Optional MP3 file attachment to play
    """
    logging.debug(f"process_play called with youtube_url={youtube_url}, youtube_title={youtube_title}, mp3_file={mp3_file}")
    
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
        try:
            # Get all current titles in the queue (lowercase for case-insensitive comparison)
            queue_titles = set(entry.title.lower() for entry in queue)
            
            # Try to find a non-duplicate YouTube result
            entry = await find_non_duplicate_youtube_result(youtube_title, queue_titles, interaction)
            
            if entry:
                queue_manager.add_to_queue(server_id, entry)
                if not interaction.guild.voice_client.is_playing():
                    await playback_manager.play_audio(interaction, entry)
                await interaction.followup.send(f"Added '{entry.title}' to the queue.")
            else:
                await interaction.followup.send("Could not find a unique track that isn't already in the queue.")

        except Exception as e:
            logging.error(f"Error in play command: {e}")
            print((f"Error in play command: {e}"))
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

async def find_non_duplicate_youtube_result(search_query: str, queue_titles: Set[str], interaction: Interaction, max_attempts: int = 10) -> Optional[QueueEntry]:
    """
    Search YouTube for a track that isn't already in the queue.
    
    Args:
        search_query: The search query to use
        queue_titles: Set of lowercase titles already in the queue
        interaction: The Discord interaction object
        max_attempts: Maximum number of search attempts
        
    Returns:
        QueueEntry if a non-duplicate is found, None otherwise
    """
    logging.info(f"Searching for non-duplicate YouTube result for: {search_query}")
    
    # If the search query is an artist only, append "music" to get better results
    if " - " not in search_query:
        search_query = f"{search_query} music"
    
    # Extract artist name for additional searches if needed
    artist_name = extract_artist_from_input(search_query)
    
    # Try the original search first
    entry = await search_youtube_for_non_duplicate(search_query, queue_titles)
    if entry:
        return entry
    
    # If original search resulted in a duplicate, try searching for more tracks by the artist
    if " - " in search_query:  # Only do this for artist - title format
        logging.info(f"Original search resulted in duplicate, trying more tracks by {artist_name}")
        
        # Get top tracks for this artist from Last.fm
        try:
            top_tracks = await get_lastfm_top_tracks(artist_name, limit=20)  # Increased limit for more options
            
            # Try each track until we find a non-duplicate
            attempts = 0
            for track in top_tracks:
                if attempts >= max_attempts:
                    break
                    
                attempts += 1
                track_title = f"{track['artist']} - {track['title']}"
                
                # Skip if this track title is already in the queue
                if is_title_duplicate(track_title, queue_titles):
                    logging.info(f"Skipping duplicate track title: {track_title}")
                    continue
                
                # Try to search YouTube for this track
                entry = await search_youtube_for_non_duplicate(track_title, queue_titles)
                if entry:
                    return entry
        except Exception as e:
            logging.error(f"Error getting Last.fm top tracks: {e}")
    
    # If we still don't have a result, try with "official audio" or "official video" appended
    for suffix in ["official audio", "official video", "lyrics", "live", "acoustic"]:
        modified_query = f"{search_query} {suffix}"
        logging.info(f"Trying modified search: {modified_query}")
        
        entry = await search_youtube_for_non_duplicate(modified_query, queue_titles)
        if entry:
            return entry
    
    # If we still don't have a result, try similar artists
    try:
        similar_artists = await get_lastfm_similar_artists(artist_name, limit=10)
        
        attempts = 0
        for similar_artist in similar_artists:
            if attempts >= max_attempts:
                break
                
            # Get top tracks for similar artist
            similar_artist_tracks = await get_lastfm_top_tracks(similar_artist, limit=5)
            
            for track in similar_artist_tracks:
                if attempts >= max_attempts:
                    break
                    
                attempts += 1
                track_title = f"{track['artist']} - {track['title']}"
                
                # Skip if this track title is already in the queue
                if is_title_duplicate(track_title, queue_titles):
                    logging.info(f"Skipping duplicate track title: {track_title}")
                    continue
                
                # Try to search YouTube for this track
                entry = await search_youtube_for_non_duplicate(track_title, queue_titles)
                if entry:
                    return entry
    except Exception as e:
        logging.error(f"Error getting similar artists: {e}")
    
    # No non-duplicate found after all attempts
    return None

async def search_youtube_for_non_duplicate(search_query: str, queue_titles: Set[str], max_results: int = 5) -> Optional[QueueEntry]:
    """
    Search YouTube for a specific query and check if the result is already in the queue.
    
    Args:
        search_query: The search query to use
        queue_titles: Set of lowercase titles already in the queue
        max_results: Maximum number of results to check
        
    Returns:
        QueueEntry if a non-duplicate is found, None otherwise
    """
    try:
        # Use ytsearch5 to get multiple results instead of just one
        yt_search_query = f"ytsearch{max_results}:{search_query}"
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'ignoreerrors': True,
            'cookiefile': 'cookies.txt',
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.get_running_loop().run_in_executor(None, lambda: ydl.extract_info(yt_search_query, download=False))

        if not info or 'entries' not in info or not info['entries']:
            logging.warning(f"No videos found for search: {search_query}")
            return None

        # Check each result until we find a non-duplicate
        for video in info['entries']:
            if not video:
                continue
                
            video_url = video.get('webpage_url')
            title = video.get('title')
            thumbnail = video.get('thumbnail')
            duration = video.get('duration', 0)
            
            # Skip videos that are too long (over 10 minutes)
            if duration > 600:
                logging.info(f"Skipping long video: {title} ({duration} seconds)")
                continue
                
            best_audio_url = next((f['url'] for f in video.get('formats', []) if f.get('acodec') != 'none'), video_url)

            # Check if this YouTube result is already in the queue
            if is_title_duplicate(title, queue_titles):
                logging.info(f"YouTube result '{title}' is already in the queue, checking next result")
                continue

            entry = QueueEntry(
                video_url=video_url,
                best_audio_url=best_audio_url,
                title=title,
                is_playlist=False,
                thumbnail=thumbnail,
                duration=duration
            )

            return entry

        # If we get here, all results were duplicates
        logging.info(f"All {len(info['entries'])} results for '{search_query}' were duplicates")
        return None

    except Exception as e:
        logging.error(f"Error searching YouTube: {e}")
        return None

def is_title_duplicate(title: str, queue_titles: Set[str]) -> bool:
    """
    Check if a title is a duplicate in the queue.
    
    Args:
        title: The title to check
        queue_titles: Set of lowercase titles already in the queue
        
    Returns:
        True if the title is a duplicate, False otherwise
    """
    # Convert to lowercase for case-insensitive comparison
    title_lower = title.lower()
    
    # Direct match
    if title_lower in queue_titles:
        return True
    
    # Try to normalize the title to handle slight variations
    normalized_title = normalize_title(title_lower)
    
    # Check if any queue title is similar enough to be considered a duplicate
    for queue_title in queue_titles:
        normalized_queue_title = normalize_title(queue_title)
        
        # If normalized titles match, consider it a duplicate
        if normalized_title == normalized_queue_title:
            return True
        
        # If one title contains the other completely, consider it a duplicate
        if normalized_title in normalized_queue_title or normalized_queue_title in normalized_title:
            # Only consider it a duplicate if the length difference is small
            if abs(len(normalized_title) - len(normalized_queue_title)) < 10:
                return True
    
    return False

def normalize_title(title: str) -> str:
    """
    Normalize a title to handle slight variations.
    
    Args:
        title: The title to normalize
        
    Returns:
        Normalized title
    """
    # Remove common words and characters that don't affect the core song identity
    title = re.sub(r'\b(official|video|audio|lyrics|hd|4k|remix|version|feat|ft|featuring|prod|by)\b', '', title, flags=re.IGNORECASE)
    
    # Remove parentheses and brackets and their contents
    title = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', title)
    
    # Remove special characters and extra spaces
    title = re.sub(r'[^\w\s]', '', title)
    
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title

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

    # Create multiple embeds if needed
    max_fields_per_embed = 25
    queue_embeds = []
    for i in range(0, len(fields), max_fields_per_embed):
        queue_embeds.append(create_embed("Current Queue", f"Total tracks: {len(queue)}", fields[i:i + max_fields_per_embed]))

    for embed in queue_embeds:
        await interaction.channel.send(embed=embed)

async def process_remove_queue(interaction: Interaction, index: int):
    logging.debug(f"Remove queue command executed for index: {index}")
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    if not queue:
        await interaction.response.send_message("The queue is currently empty.")
        return

    if index < 1 or index > len(queue):
        await interaction.response.send_message(f"Invalid index. Please provide a number between 1 and {len(queue)}.")
        return

    entry = queue.pop(index - 1)
    queue_manager.save_queues()
    if entry.best_audio_url.startswith("downloaded-mp3s/"):
        await delete_file(entry.best_audio_url)
    await interaction.response.send_message(f"Removed '{entry.title}' from the queue.")

async def process_skip(interaction: Interaction):
    logging.debug("Skip command executed")
    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
        await interaction.response.send_message("Nothing is currently playing.")
        return

    interaction.guild.voice_client.stop()
    await interaction.response.send_message("Skipped the current track.")

async def process_pause(interaction: Interaction):
    logging.debug("Pause command executed")
    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
        await interaction.response.send_message("Nothing is currently playing.")
        return

    interaction.guild.voice_client.pause()
    await interaction.response.send_message("Paused the current track.")

async def process_resume(interaction: Interaction):
    logging.debug("Resume command executed")
    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_paused():
        await interaction.response.send_message("Nothing is currently paused.")
        return

    interaction.guild.voice_client.resume()
    await interaction.response.send_message("Resumed playback.")

async def process_stop(interaction: Interaction):
    logging.debug("Stop command executed")
    if not interaction.guild.voice_client:
        await interaction.response.send_message("The bot is not connected to a voice channel.")
        return

    if interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.stop()
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("Stopped playback and disconnected from the voice channel.")

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
    
async def discover_and_queue_recommendations(interaction, artist_or_song: Optional[str] = None):
    """
    Discover and queue songs based on the current song or input artist, avoiding duplicates across all artists.
    
    Args:
        interaction: The Discord interaction object
        artist_or_song: Optional artist or song to use as seed instead of currently playing track
        
    Returns:
        Tuple containing (number of tracks queued, seed used, source of recommendations)
    """
    server_id = str(interaction.guild.id)
    queue_manager.ensure_queue_exists(server_id)
    current_queue = queue_manager.get_queue(server_id)
    
    # Get all current titles in the queue (lowercase for case-insensitive comparison)
    queue_titles = set(entry.title.lower() for entry in current_queue)
    
    # 1. Determine seed
    currently_playing = queue_manager.currently_playing
    seed = artist_or_song or (currently_playing.title if currently_playing else None)

    if not seed:
        await interaction.followup.send("No song is currently playing and no input was provided.")
        return 0, "None", "Last.fm"

    logging.info(f"🌱 Discovery seed: {seed}")
    artist_name = extract_artist_from_input(seed)
    
    # Track artists we've already processed to avoid duplicates
    processed_artists = set()
    total_queued = 0
    max_attempts = 10  # Increased limit for more thorough search
    target_tracks = 8  # Target number of tracks to queue
    
    try:
        # 2. Get similar artists from Last.fm
        similar_artists = await get_lastfm_similar_artists(artist_name, limit=20)  # Get more similar artists
        if not similar_artists:
            await interaction.followup.send(f"No similar artists found for {artist_name}.")
            return 0, seed, "Last.fm"
        
        # Add seed artist to the list of artists to process
        all_artists = [artist_name] + similar_artists
        queued_tracks = []
        attempts = 0
        
        # 3. Process artists one by one until we have enough tracks or run out of attempts
        artist_index = 0
        while total_queued < target_tracks and attempts < max_attempts and artist_index < len(all_artists):
            current_artist = all_artists[artist_index]
            artist_index += 1
            
            if current_artist.lower() in processed_artists:
                continue
                
            processed_artists.add(current_artist.lower())
            logging.info(f"Processing artist: {current_artist} ({artist_index}/{len(all_artists)})")
            
            # Get more tracks per artist (15 instead of 10)
            artist_tracks = await get_lastfm_top_tracks(current_artist, limit=5)
            if not artist_tracks:
                logging.info(f"No tracks found for artist: {current_artist}")
                continue
                
            # Try each track from this artist
            for track in artist_tracks:
                if total_queued >= target_tracks or attempts >= max_attempts:
                    break
                    
                attempts += 1
                track_title = f"{track['artist']} - {track['title']}"
                
                # Skip if this track title is already in the queue
                if is_title_duplicate(track_title, queue_titles):
                    logging.info(f"Skipping duplicate track title: {track_title}")
                    continue
                
                # Try to find a non-duplicate YouTube result for this track
                try:
                    # Get all current titles in the queue (lowercase for case-insensitive comparison)
                    current_queue_titles = set(entry.title.lower() for entry in queue_manager.get_queue(server_id))
                    
                    # Try to find a non-duplicate YouTube result
                    entry = await find_non_duplicate_youtube_result(track_title, current_queue_titles, interaction)
                    
                    if entry:
                        queue_manager.add_to_queue(server_id, entry)
                        queue_titles.add(entry.title.lower())  # Add to our tracking set
                        queued_tracks.append(entry.title)
                        total_queued += 1
                        logging.info(f"Added track {total_queued}/{target_tracks}: {entry.title}")
                    else:
                        logging.info(f"Could not find a unique YouTube result for: {track_title}")
                except Exception as e:
                    logging.error(f"Error queuing track {track_title}: {e}")
        
        # 4. If we still need more tracks, try to find additional artists by genre
        if total_queued < target_tracks:
            logging.info(f"Only found {total_queued} tracks, looking for more by genre")
            
            # Get artist tags (genres)
            artist_tags = await get_artist_tags(artist_name)
            
            # Try each tag to find more tracks
            for tag in artist_tags:
                if total_queued >= target_tracks:
                    break
                    
                logging.info(f"Looking for tracks with tag: {tag}")
                tag_tracks = await get_tracks_by_tag(tag, queue_titles, limit=5)
                
                for track in tag_tracks:
                    if total_queued >= target_tracks or attempts >= max_attempts:
                        break
                        
                    attempts += 1
                    track_title = f"{track['artist']} - {track['title']}"
                    
                    # Skip if this track title is already in the queue
                    if is_title_duplicate(track_title, queue_titles):
                        logging.info(f"Skipping duplicate track title: {track_title}")
                        continue
                    
                    # Try to find a non-duplicate YouTube result for this track
                    try:
                        # Get all current titles in the queue (lowercase for case-insensitive comparison)
                        current_queue_titles = set(entry.title.lower() for entry in queue_manager.get_queue(server_id))
                        
                        # Try to find a non-duplicate YouTube result
                        entry = await find_non_duplicate_youtube_result(track_title, current_queue_titles, interaction)
                        
                        if entry:
                            queue_manager.add_to_queue(server_id, entry)
                            queue_titles.add(entry.title.lower())  # Add to our tracking set
                            queued_tracks.append(entry.title)
                            total_queued += 1
                            logging.info(f"Added track {total_queued}/{target_tracks}: {entry.title}")
                        else:
                            logging.info(f"Could not find a unique YouTube result for: {track_title}")
                    except Exception as e:
                        logging.error(f"Error queuing track {track_title}: {e}")
        
        # 5. If we still need more tracks, use popular tracks as a last resort
        if total_queued < target_tracks:
            logging.info(f"Still only found {total_queued} tracks, using popular tracks")
            
            popular_tracks = await get_popular_tracks(queue_titles, limit=20)
            
            for track in popular_tracks:
                if total_queued >= target_tracks or attempts >= max_attempts:
                    break
                    
                attempts += 1
                track_title = f"{track['artist']} - {track['title']}"
                
                # Skip if this track title is already in the queue
                if is_title_duplicate(track_title, queue_titles):
                    logging.info(f"Skipping duplicate track title: {track_title}")
                    continue
                
                # Try to find a non-duplicate YouTube result for this track
                try:
                    # Get all current titles in the queue (lowercase for case-insensitive comparison)
                    current_queue_titles = set(entry.title.lower() for entry in queue_manager.get_queue(server_id))
                    
                    # Try to find a non-duplicate YouTube result
                    entry = await find_non_duplicate_youtube_result(track_title, current_queue_titles, interaction)
                    
                    if entry:
                        queue_manager.add_to_queue(server_id, entry)
                        queue_titles.add(entry.title.lower())  # Add to our tracking set
                        queued_tracks.append(entry.title)
                        total_queued += 1
                        logging.info(f"Added track {total_queued}/{target_tracks}: {entry.title}")
                    else:
                        logging.info(f"Could not find a unique YouTube result for: {track_title}")
                except Exception as e:
                    logging.error(f"Error queuing track {track_title}: {e}")
        
        # 6. Display the list of tracks added to the queue
        if queued_tracks:
            # Create an embed to display the tracks
            embed = Embed(
                title="🎵 Discovered Tracks Added to Queue",
                description=f"Based on: **{seed}**\nTotal tracks added: **{len(queued_tracks)}**",
                color=0x3498db  # Blue color
            )
            
            # Add each track as a field in the embed
            for i, track_title in enumerate(queued_tracks):
                embed.add_field(
                    name=f"{i+1}. {track_title}",
                    value="\u200b",  # Zero-width space as a placeholder
                    inline=False
                )
            
            # Send the embed to the channel
            await interaction.followup.send(embed=embed)
            
            # If there's a currently playing track, send a Now Playing Menu for it
            if queue_manager.currently_playing:
                await ButtonView.send_now_playing_for_buttons(interaction, queue_manager.currently_playing)
            # If there's no currently playing track but we added tracks to the queue, send a Now Playing Menu for the first track
            elif queued_tracks and server_id in queue_manager.queues and queue_manager.queues[server_id]:
                await ButtonView.send_now_playing_for_buttons(interaction, queue_manager.queues[server_id][0])
            
            logging.info(f"Successfully queued {len(queued_tracks)} tracks: {', '.join(queued_tracks)}")
            logging.info(f"Made {attempts} attempts to find unique tracks")
        else:
            logging.warning(f"Failed to queue any tracks after {attempts} attempts")
                
        return total_queued, seed, "Last.fm"
        
    except Exception as e:
        logging.error(f"Error in discover_and_queue_recommendations: {e}")
        await interaction.followup.send(f"An error occurred while discovering songs: {str(e)}")
        return 0, seed, "Last.fm"

def extract_artist_from_input(text: str) -> str:
    """Extract artist name from a string that may include a song title."""
    if " - " in text:
        return text.split(" - ")[0].strip()
    return text.strip()

async def get_lastfm_similar_artists(artist_name: str, limit: int = 10) -> List[str]:
    """
    Get similar artists from Last.fm API.
    
    Args:
        artist_name: The name of the artist to find similar artists for
        limit: Maximum number of similar artists to return
        
    Returns:
        List of similar artist names
    """
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist={quote_plus(artist_name)}&api_key={LASTFM_API_KEY}&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                logging.info(f"Last.fm similar artists status: {resp.status}")
                data = await resp.json()
                artists = data.get("similarartists", {}).get("artist", [])
                return [artist["name"] for artist in artists[:limit]]
    except Exception as e:
        logging.error(f"Failed to get similar artists from Last.fm: {e}")
        return []
    
async def get_lastfm_top_tracks(artist_name: str, limit: int = 10) -> List[Dict]:
    """
    Get top tracks for an artist from Last.fm API.
    
    Args:
        artist_name: The name of the artist to get top tracks for
        limit: Maximum number of tracks to return
        
    Returns:
        List of dictionaries containing artist and title information
    """
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist={quote_plus(artist_name)}&api_key={LASTFM_API_KEY}&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                logging.info(f"Last.fm top tracks status for {artist_name}: {resp.status}")
                data = await resp.json()
                tracks = data.get("toptracks", {}).get("track", [])
                return [{"artist": artist_name, "title": track["name"]} for track in tracks[:limit]]
    except Exception as e:
        logging.error(f"Failed to get top tracks for {artist_name} from Last.fm: {e}")
        return []

async def get_artist_tags(artist_name: str, limit: int = 5) -> List[str]:
    """
    Get tags (genres) for an artist from Last.fm API.
    
    Args:
        artist_name: The name of the artist to get tags for
        limit: Maximum number of tags to return
        
    Returns:
        List of tag names
    """
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={quote_plus(artist_name)}&api_key={LASTFM_API_KEY}&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                logging.info(f"Last.fm artist info status for {artist_name}: {resp.status}")
                data = await resp.json()
                tags = data.get("artist", {}).get("tags", {}).get("tag", [])
                return [tag["name"] for tag in tags[:limit]]
    except Exception as e:
        logging.error(f"Failed to get tags for {artist_name} from Last.fm: {e}")
        return ["rock", "pop"]  # Default tags if we can't get any

async def get_tracks_by_tag(tag: str, queue_titles: Set[str], limit: int = 10) -> List[Dict]:
    """
    Get top tracks for a tag (genre) from Last.fm API.
    
    Args:
        tag: The tag to get tracks for
        queue_titles: Set of lowercase titles already in the queue
        limit: Maximum number of tracks to return
        
    Returns:
        List of dictionaries containing artist and title information
    """
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=tag.gettoptracks&tag={quote_plus(tag)}&api_key={LASTFM_API_KEY}&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                logging.info(f"Last.fm tag top tracks status for {tag}: {resp.status}")
                data = await resp.json()
                tracks = data.get("tracks", {}).get("track", [])
                
                # Filter out tracks that are already in the queue
                result = []
                for track in tracks:
                    track_title = f"{track['artist']['name']} - {track['name']}"
                    if not is_title_duplicate(track_title, queue_titles):
                        result.append({"artist": track['artist']['name'], "title": track['name']})
                        if len(result) >= limit:
                            break
                
                return result
    except Exception as e:
        logging.error(f"Failed to get tracks for tag {tag} from Last.fm: {e}")
        return []

async def get_popular_tracks(queue_titles: Set[str], limit: int = 10) -> List[Dict]:
    """
    Get popular tracks from Last.fm API.
    
    Args:
        queue_titles: Set of lowercase titles already in the queue
        limit: Maximum number of tracks to return
        
    Returns:
        List of dictionaries containing artist and title information
    """
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=chart.gettoptracks&api_key={LASTFM_API_KEY}&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                logging.info(f"Last.fm chart top tracks status: {resp.status}")
                data = await resp.json()
                tracks = data.get("tracks", {}).get("track", [])
                
                # Filter out tracks that are already in the queue
                result = []
                for track in tracks:
                    track_title = f"{track['artist']['name']} - {track['name']}"
                    if not is_title_duplicate(track_title, queue_titles):
                        result.append({"artist": track['artist']['name'], "title": track['name']})
                        if len(result) >= limit:
                            break
                
                return result
    except Exception as e:
        logging.error(f"Failed to get popular tracks from Last.fm: {e}")
        return []
