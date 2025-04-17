import re
import aiohttp
import yt_dlp
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
# from pydub import AudioSegment
from mutagen.mp3 import MP3
import logging
import os
import asyncio
from discord import Embed, FFmpegPCMAudio, PCMVolumeTransformer, Interaction
from discord.utils import get
from discord.errors import NotFound
from lyricsgenius import Genius
from dotenv import load_dotenv
import config  # ✅ Import your config to access MUSICBRAINZ_USER_AGENT

load_dotenv()

# Global rate limit lock and timer
musicbrainz_lock = asyncio.Lock()
last_musicbrainz_call = 0

logging.basicConfig(level=logging.DEBUG, filename='utils.log', format='%(asctime)s:%(levelname)s:%(message)s')

# Access the Genius API token
GENIUS_API_TOKEN = os.getenv('genius_api_token')

# Initialize the Genius API client
genius = Genius(GENIUS_API_TOKEN)

executor = ThreadPoolExecutor(max_workers=1)

UNWANTED_PATTERNS = [
    r'\(Official Video\)', 
    r'\(Official Audio\)', 
    r'\(Audio\)',
    r'\(Official Lyric Video\)', 
    r'\(Visualizer\)', 
    r'\(audio only\)', 
    r'\(Official Music Video\)', 
    r'\[Official Visualizer\]',
    r'\(Lyrics\)',
    r'\(Lyric Video\)',
    r'\[Lyrics\]',
    r'\(HD\)',
    r'\[HD\]',
    r'\[ Official Music Video \]',
    r'\[ Official Visualizer \]',
    r'\[ Visualizer \]',
    # Add more patterns as needed
]

async def rate_limited_musicbrainz_get(session, url):
    global last_musicbrainz_call

    try:
        async with musicbrainz_lock:
            now = asyncio.get_event_loop().time()
            wait_time = 1.5 - (now - last_musicbrainz_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            last_musicbrainz_call = asyncio.get_event_loop().time()

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logging.warning(f"MusicBrainz request failed with status {response.status} for URL: {url}")
                    return {}
                return await response.json()

    except asyncio.TimeoutError:
        logging.error(f"Timeout during MusicBrainz request: {url}")
        return {}

    except aiohttp.ClientError as e:
        logging.error(f"Client error during MusicBrainz request: {url} — {e}")
        return {}

    except Exception as e:
        logging.exception(f"Unexpected error during MusicBrainz request: {url} — {e}")
        return {}

def sanitize_title(title: str) -> str:
    """
    Sanitize the given title by removing unwanted characters and patterns.

    Args:
        title (str): The original title of the song.

    Returns:
        str: The sanitized title.
    """
    logging.debug(f"Sanitizing title: {title}")
    print(f"Sanitizing title: {title}")
    # Define a pattern to match characters that are not allowed in file names.
    illegal_characters_pattern = r'[<>:"/\\|?*]'
    
    # Remove illegal characters from the title.
    sanitized_title = re.sub(illegal_characters_pattern, '', title, flags=re.IGNORECASE)
    logging.debug(f"Title after removing illegal characters: {sanitized_title}")
    print(f"Title after removing illegal characters: {sanitized_title}")
    
    # Remove unwanted patterns defined in UNWANTED_PATTERNS from the title.
    for unwanted_pattern in UNWANTED_PATTERNS:
        sanitized_title = re.sub(unwanted_pattern, '', sanitized_title, flags=re.IGNORECASE).strip()
        logging.debug(f"Title after removing pattern '{unwanted_pattern}': {sanitized_title}")
        print(f"Title after removing pattern '{unwanted_pattern}': {sanitized_title}")
    
    return sanitized_title

def sanitize_filename(filename: str) -> str:
    logging.debug(f"Sanitizing filename: {filename}")
    print(f"Sanitizing filename: {filename}")
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename)

async def download_file(url: str, dest_folder: str) -> str:
    logging.debug(f"Downloading file from URL: {url}")
    print(f"Downloading file from URL: {url}")
    os.makedirs(dest_folder, exist_ok=True)
    filename = sanitize_filename(os.path.basename(url))
    file_path = os.path.join(dest_folder, filename)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    f.write(await response.read())
                logging.info(f"Downloaded file: {file_path}")
                print(f"Downloaded file: {file_path}")
                return file_path
            else:
                logging.error(f"Failed to download file: {url}")
                print(f"Failed to download file: {url}")
                return None

def extract_mp3_metadata(file_path: str) -> dict:
    audio = MP3(file_path)
    title = audio.get('TIT2', os.path.basename(file_path)).text[0] if audio.get('TIT2') else os.path.basename(file_path)
    artist = audio.get('TPE1', '').text[0] if audio.get('TPE1') else ''
    thumbnail = None
    if 'APIC:' in audio:
        thumbnail = audio['APIC:'].data
    duration = int(audio.info.length) if audio.info else 0
    return {
        'title': f"{artist} - {title}".strip(' - '),
        'thumbnail': thumbnail,
        'duration': duration
    }

async def delete_file(file_path: str):
    if os.path.exists(file_path):
        os.remove(file_path)
        logging.info(f"Deleted file: {file_path}")
    else:
        logging.warning(f"File not found for deletion: {file_path}")
        
async def get_similar_tracks_from_musicbrainz(artist_name, limit=5):
    import urllib.parse
    import aiohttp
    import asyncio
    import logging

    headers = {
        "User-Agent": config.MUSICBRAINZ_USER_AGENT
    }

    recordings = []

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # Step 1: Search for artist MBID
            search_url = f"https://musicbrainz.org/ws/2/artist/?query=artist:{urllib.parse.quote(artist_name)}&fmt=json"
            logging.info(f"🔍 Looking up MBID for seed artist: {artist_name} | URL: {search_url}")
            async with session.get(search_url) as res:
                data = await res.json()
                if not data.get('artists'):
                    logging.warning(f"⚠️ No artist found for {artist_name}")
                    return []
                mbid = data['artists'][0]['id']
                logging.info(f"✅ Found MBID for artist '{artist_name}': {mbid}")

            # Step 2: Get related artists
            rel_url = f"https://musicbrainz.org/ws/2/artist/{mbid}?inc=artist-rels&fmt=json"
            logging.info(f"🔗 Getting related artists for MBID: {mbid} | URL: {rel_url}")
            async with session.get(rel_url) as res:
                data = await res.json()
                related = [
                    rel['artist']['name']
                    for rel in data.get('relations', [])
                    if rel.get('type') in ["influenced by", "similar to", "collaboration"]
                ][:limit]
                logging.info(f"🎯 Related artists found: {related}")

            # Step 3: For each related artist, get a few recordings
            for rel_artist in related:
                try:
                    encoded_artist = urllib.parse.quote(f'"{rel_artist}"')
                    track_url = f"https://musicbrainz.org/ws/2/recording/?query=artist:{encoded_artist}&limit=2&fmt=json"
                    logging.info(f"🎶 Searching for top tracks of '{rel_artist}' | URL: {track_url}")

                    async with session.get(track_url) as res:
                        rdata = await res.json()
                        for recording in rdata.get('recordings', []):
                            title = recording.get('title')
                            if title:
                                track_string = f"{rel_artist} - {title}"
                                recordings.append(track_string)
                                logging.info(f"🎧 Found track: {track_string}")
                except Exception as e:
                    logging.error(f"❌ Failed to fetch tracks for '{rel_artist}': {e}")
                await asyncio.sleep(1.5)  # Rate limit buffer
    except Exception as e:
        logging.error(f"🚨 Failed to fetch similar tracks from MusicBrainz for artist '{artist_name}': {e}")

    logging.info(f"✅ MusicBrainz suggestions for '{artist_name}': {recordings}")
    return recordings

async def fetch_info(url, index: int = None):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': False if "list=" in url else True,
        'playlist_items': str(index) if index is not None else None,
        'ignoreerrors': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.debug(f"Fetching info for URL: {url}, index: {index}")
            info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
            if 'entries' in info:
                entries = []
                for entry in info['entries']:
                    if entry and not entry.get('is_unavailable', False):
                        entry['duration'] = entry.get('duration', 0)
                        entry['thumbnail'] = entry.get('thumbnail', '')
                        entry['best_audio_url'] = next((f['url'] for f in entry['formats'] if f.get('acodec') != 'none'), entry.get('url'))
                        entries.append(entry)
                        logging.debug(f"Processing entry: {entry.get('title', 'Unknown title')}")
                info['entries'] = entries
            else:
                info['duration'] = info.get('duration', 0)
                info['thumbnail'] = info.get('thumbnail', '')
                info['best_audio_url'] = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), info.get('url'))
                logging.debug(f"Processing entry: {info.get('title', 'Unknown title')}")
            return info
    except yt_dlp.utils.ExtractorError as e:
        logging.warning(f"Skipping unavailable video: {str(e)}")
        return None
    
def create_now_playing_embed(entry):
    embed = Embed(title="Now Playing", description=entry.title, url=entry.video_url)
    embed.set_thumbnail(url=entry.thumbnail)

    favorited_by = ', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else "No one"
    embed.add_field(name="Favorited by", value=favorited_by, inline=False)

    duration = entry.duration if hasattr(entry, 'duration') else 300
    progress_bar, elapsed_str, duration_str = create_progress_bar(0, duration)
    embed.add_field(name="Progress", value=f"{progress_bar} {elapsed_str} / {duration_str}", inline=False)

    return embed

def store_message_info(bot, message_id, view):
    bot.message_views[message_id] = view
    bot.add_now_playing_message(message_id)
    
def is_playback_active(interaction):
    return interaction.guild.voice_client and interaction.guild.voice_client.is_playing()
    
def is_entry_currently_playing(entry, queue_manager):
    return queue_manager.currently_playing == entry

async def finalize_progress_update(interaction, message, entry, duration, button_view):
    elapsed = calculate_elapsed_time(entry, duration)
    progress_bar, elapsed_str, duration_str = create_progress_bar(elapsed / duration, duration)
    embed = update_embed_fields(message.embeds[0], entry, progress_bar, elapsed_str, duration_str)
    view = button_view(interaction.client, entry, paused=False, current_user=interaction.user)
    await message.edit(embed=embed, view=view)

async def update_progress_bar(interaction, message, entry, button_view, queue_manager):
    logging.debug(f"Updating progress bar for: {entry.title}")
    duration = entry.duration if hasattr(entry, 'duration') else 300

    while not queue_manager.is_paused:
        print(f'{is_playback_active(interaction)}  is playback active --- checking for opposite')
        if not is_entry_currently_playing(entry, queue_manager):
            logging.info(f"Stopping progress update for {entry.title}")
            break

        if not is_playback_active(interaction):
            await finalize_progress_update(interaction, message, entry, duration, button_view)
            break

        await refresh_progress_bar(interaction, message, entry, duration, button_view)
        await asyncio.sleep(2)  # Update less frequently to reduce load
        
def create_progress_bar(progress, duration):
    total_blocks = 20
    filled_blocks = int(progress * total_blocks)
    progress_bar = "[" + "=" * filled_blocks + " " * (total_blocks - filled_blocks) + "]"
    elapsed_str = str(timedelta(seconds=int(progress * duration)))
    duration_str = str(timedelta(seconds=duration))
    return progress_bar, elapsed_str, duration_str

async def refresh_progress_bar(interaction, message, entry, duration, button_view):
    elapsed = calculate_elapsed_time(entry, duration)
    progress_bar, elapsed_str, duration_str = create_progress_bar(elapsed / duration, duration)
    embed = update_embed_fields(message.embeds[0], entry, progress_bar, elapsed_str, duration_str)
    view = button_view(interaction.client, entry, paused=False, current_user=interaction.user)
    await message.edit(embed=embed, view=view)

async def schedule_progress_bar_update(ctx_or_interaction, message, entry, button_view, queue_manager):
    await update_progress_bar(ctx_or_interaction, message, entry, button_view, queue_manager)
    asyncio.create_task(update_progress_bar(ctx_or_interaction, message, entry, button_view, queue_manager))
    
def calculate_elapsed_time(entry, duration):
    elapsed = (datetime.now() - entry.start_time - entry.paused_duration).total_seconds()
    return min(elapsed, duration)

def update_embed_fields(embed, entry, progress_bar, elapsed_str, duration_str):
    favorited_by = ', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else "No one"
    embed.set_field_at(0, name="Favorited by", value=favorited_by, inline=False)
    embed.set_field_at(1, name="Progress", value=f"{progress_bar} {elapsed_str} / {duration_str}", inline=False)
    return embed

async def get_lyrics(query: str) -> str:
    def process_lyrics(lyrics: str) -> str:
        lyrics = re.sub(r'(?i).*Lyrics', 'Lyrics', lyrics, count=1, flags=re.IGNORECASE).strip()
        lyrics = re.sub(r'(?i)Embed.*$', '', lyrics, flags=re.IGNORECASE).strip()
        if re.match(r'(?i)lyrics', lyrics[:15]):
            lyrics = re.sub(r'(?i)lyrics', '', lyrics, count=1).strip()
        return lyrics

    def validate_lyrics(lyrics: str, title: str, artist: str) -> bool:
        return title.lower() in lyrics.lower() and any(artist_part.lower() in song.artist.lower() for artist_part in artist.split())

    try:
        artist, title = None, None
        print(f"Original query: {query}")
        possible_splits = re.split(r' - | by | from | @ | \| ', query, maxsplit=1)
        print(f"Possible splits: {possible_splits}")

        if len(possible_splits) == 2:
            artist, title = possible_splits
            print(f"Extracted artist: {artist.strip()}, title: {title.strip()}")
            song = genius.search_song(title.strip(), artist.strip())
            if song:
                lyrics = process_lyrics(song.lyrics)
                print(f"Lyrics after processing:\n{lyrics}")
                if validate_lyrics(lyrics, title.strip(), artist.strip()):
                    print(f"Lyrics found for {artist.strip()} - {title.strip()}")
                    return f"Lyrics for {artist.strip()} - {title.strip()}\n\n{lyrics}"
                # else:
                #     print(f"Lyrics not found for {title.strip()} by {artist.strip()}")
                #     return f"Lyrics not found for {title.strip()} by {artist.strip()}"

        print(f"Searching with the entire query: {query}")
        song = genius.search_song(query)
        if song:
            lyrics = process_lyrics(song.lyrics)
            print(f"Lyrics after processing:\n{lyrics}")
            if validate_lyrics(lyrics, song.title, song.artist):
                print(f"Lyrics found for {song.artist} - {song.title}")
                return f"Lyrics for {song.artist} - {song.title}\n\n{lyrics}"
            else:
                print(f"Lyrics not found for {song.title} by {song.artist}")
                return f"Lyrics not found for {song.title} by {song.artist}"

        print("Lyrics not found.")
        return "Lyrics not found."
    except Exception as e:
        logging.error(f"Error fetching lyrics: {e}")
        print(f"Exception: {e}")
        return "An error occurred while fetching the lyrics."
    
async def remove_orphaned_mp3_files(queue_manager, download_folder: str = 'downloaded-mp3s'):
    """Remove MP3 files that are not in the current queues."""
    logging.debug("Checking for orphaned MP3 files.")
    all_entries = [entry for queue in queue_manager.queues.values() for entry in queue]
    all_mp3_files = {entry.best_audio_url for entry in all_entries if entry.best_audio_url.startswith(download_folder)}
    
    for root, _, files in os.walk(download_folder):
        for file in files:
            file_path = os.path.join(root, file)
            if file_path not in all_mp3_files:
                await delete_file(file_path)
                logging.info(f"Deleted orphaned MP3 file: {file_path}")