import logging
from discord.ext import commands
from discord import Attachment, Interaction, app_commands
from queue_manager import queue_manager
from config import LASTFM_API_KEY
from urllib.parse import quote_plus
import aiohttp
import asyncio
import aiohttp
from playback import PlaybackManager
from typing import Optional
from yt_dlp import YoutubeDL
from command_functions import (
    process_help,
    process_play_next,
    process_play,
    process_previous,
    process_remove_by_title,
    process_shuffle,
    process_play_queue,
    process_list_queue,
    process_remove_queue,
    process_skip,
    process_pause,
    process_resume,
    process_stop,
    process_restart,
    process_mp3_list_next,
    process_mp3_list,
    process_clear_queue,
    process_move_to_next,
    process_search_and_play_from_queue,
    process_remove_duplicates
)

logging.basicConfig(level=logging.DEBUG, filename='commands.log', format='%(asctime)s:%(levelname)s:%(message)s')

playback_manager = PlaybackManager(queue_manager)

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.debug("Initializing MusicCommands Cog")
        # Initialize pandora_tasks dictionary for memory management
        if not hasattr(bot, "pandora_tasks"):
            bot.pandora_tasks = {}

    async def title_autocomplete(self, interaction: Interaction, current: str):
        server_id = str(interaction.guild.id)
        queue_manager.ensure_queue_exists(server_id)
        queue = queue_manager.get_queue(server_id)
        titles = [entry.title for entry in queue if current.lower() in entry.title.lower()]
        return [app_commands.Choice(name=title, value=title) for title in titles[:25]]

    @app_commands.command(name='play_next_in_queue', description='Move a specified track to the second position in the queue.')
    async def play_next(self, interaction: Interaction, youtube_url: str = None, youtube_title: str = None, mp3_file: Optional[Attachment] = None):
        await interaction.response.defer()  # Defer the interaction response
        logging.debug(f"Play next command executed for youtube_url: {youtube_url}, youtube_title: {youtube_title}, mp3_file: {mp3_file}")
        await process_play_next(interaction, youtube_url, youtube_title, mp3_file)
        
    @app_commands.command(name='remove_duplicates', description='Remove duplicate songs from the queue based on title.')
    async def remove_duplicates(self, interaction: Interaction):
        logging.debug("Remove duplicates command triggered")
        await process_remove_duplicates(interaction)

    @app_commands.command(name='play', description='Play a YT URL, YT Title, or MP3 file if no audio is playing or add it to the end of the queue.')
    async def play(self, interaction: Interaction, youtube_url: str = None, youtube_title: str = None, mp3_file: Optional[Attachment] = None):
        await interaction.response.defer()  # Defer the interaction response
        logging.debug(f"Play command executed for youtube_url: {youtube_url}, youtube_title: {youtube_title}, mp3_file: {mp3_file}")
        await process_play(interaction, youtube_url, youtube_title, mp3_file)

    @app_commands.command(name='previous', description='Play the last entry that was being played.')
    async def previous(self, interaction: Interaction):
        logging.debug("Previous command executed")
        await process_previous(interaction)

    @app_commands.command(name='remove_by_title', description='Remove a track from the queue by title.')
    async def remove_by_title(self, interaction: Interaction, title: str):
        logging.debug(f"Remove by title command executed for title: {title}")
        await process_remove_by_title(interaction, title)

    @app_commands.command(name='shuffle', description='Shuffle the current queue.')
    async def shuffle(self, interaction: Interaction):
        logging.debug("Shuffle command executed")
        await process_shuffle(interaction)

    @app_commands.command(name='play_queue', description='Play the current queue.')
    async def play_queue(self, interaction: Interaction):
        logging.debug("Play queue command executed")
        await process_play_queue(interaction)

    @app_commands.command(name='list_queue', description='List all entries in the current queue.')
    async def list_queue(self, interaction: Interaction):
        logging.debug("List queue command executed")
        await process_list_queue(interaction)

    @app_commands.command(name='remove_queue', description='Remove a track from the queue by index.')
    async def remove_queue(self, interaction: Interaction, index: int):
        logging.debug(f"Remove queue command executed for index: {index}")
        await process_remove_queue(interaction, index)

    @app_commands.command(name='skip', description='Skip the current track.')
    async def skip(self, interaction: Interaction):
        logging.debug("Skip command executed")
        await process_skip(interaction)

    @app_commands.command(name='pause', description='Pause the currently playing track.')
    async def pause(self, interaction: Interaction):
        logging.debug("Pause command executed")
        await process_pause(interaction)

    @app_commands.command(name='resume', description='Resume playback if it is paused.')
    async def resume(self, interaction: Interaction):
        logging.debug("Resume command executed")
        await process_resume(interaction)

    @app_commands.command(name='stop', description='Stop playback and disconnect the bot from the voice channel.')
    async def stop(self, interaction: Interaction):
        logging.debug("Stop command executed")
        await process_stop(interaction)

    @app_commands.command(name='restart', description='Restart the currently playing track from the beginning.')
    async def restart(self, interaction: Interaction):
        logging.debug("Restart command executed")
        await process_restart(interaction)

    @app_commands.command(name='clear_queue', description='Clear the queue except the currently playing entry.')
    async def clear_queue(self, interaction: Interaction):
        logging.debug("Clear queue command executed")
        await process_clear_queue(interaction)

    @app_commands.command(name='move_to_next', description="Move the specified track in the queue to the second position.")
    @app_commands.autocomplete(title=title_autocomplete)
    async def move_to_next(self, interaction: Interaction, title: str):
        logging.debug(f"Move to next command executed for title: {title}")
        await process_move_to_next(interaction, title)

    @app_commands.command(name="search_and_play_from_queue", description="Search the current queue and play the specified track.")
    @app_commands.autocomplete(title=title_autocomplete)
    async def search_and_play_from_queue(self, interaction: Interaction, title: str):
        logging.debug(f"Search and play from queue command executed for title: {title}")
        await process_search_and_play_from_queue(interaction, title)

    @app_commands.command(name='help', description='Show the help text.')
    async def help_command(self, interaction: Interaction):
        logging.debug("Help command executed")
        await process_help(interaction)

    @app_commands.command(name="discover", description="Play music by mood, genre, or similar to current song.")
    @app_commands.describe(
        mood="Mood of the music (e.g., happy, chill, sad)",
        genres="Genres separated by commas (e.g., rock, electronic, jazz)"
    )
    async def discover(
        self,
        interaction: Interaction,
        mood: Optional[str] = None,
        genres: Optional[str] = None
    ):
        logging.info(f"/discover triggered by {interaction.user}")
        await interaction.response.defer(thinking=True)

        guild_id = str(interaction.guild.id)
        current_entry = queue_manager.currently_playing
        seed_artist = None
        similar_tracks = []
        processed_tracks = set()

        if current_entry:
            seed_title = current_entry.title
            try:
                query = quote_plus(seed_title)
                url = f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={query}&api_key={LASTFM_API_KEY}&format=json&limit=1"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        data = await resp.json()
                        results = data.get("results", {}).get("trackmatches", {}).get("track", [])
                        if results:
                            seed_artist = results[0]["artist"]
                            logging.info(f"Seed artist found: {seed_artist}")
            except Exception as e:
                logging.error(f"Seed artist lookup failed: {e}")

        if seed_artist:
            try:
                encoded_artist = quote_plus(seed_artist)
                url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist={encoded_artist}&api_key={LASTFM_API_KEY}&format=json&limit=5"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        data = await resp.json()
                        for artist in data.get("similarartists", {}).get("artist", []):
                            name = artist.get("name")
                            if name.lower() not in ["various artists", "[unknown]"]:
                                top_tracks_url = f"http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist={quote_plus(name)}&api_key={LASTFM_API_KEY}&format=json&limit=2"
                                async with session.get(top_tracks_url) as track_resp:
                                    track_data = await track_resp.json()
                                    tracks = track_data.get("toptracks", {}).get("track", [])
                                    for t in tracks:
                                        title = f"{name} - {t['name']}"
                                        if title not in processed_tracks:
                                            similar_tracks.append(title)
                                            processed_tracks.add(title)
            except Exception as e:
                logging.error(f"Failed to fetch similar artist tracks: {e}")

        user_tags = []
        if mood:
            user_tags.append(mood.lower())
        if genres:
            user_tags.extend([g.strip().lower() for g in genres.split(",")])

        if user_tags:
            try:
                async with aiohttp.ClientSession() as session:
                    for tag in user_tags:
                        tag_url = f"http://ws.audioscrobbler.com/2.0/?method=tag.gettopartists&tag={quote_plus(tag)}&api_key={LASTFM_API_KEY}&format=json&limit=5"
                        async with session.get(tag_url) as resp:
                            data = await resp.json()
                            top_artists = data.get("topartists", {}).get("artist", [])
                            for artist in top_artists:
                                name = artist.get("name")
                                if name.lower() not in ["various artists", "[unknown]"] and name not in processed_tracks:
                                    top_tracks_url = f"http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist={quote_plus(name)}&api_key={LASTFM_API_KEY}&format=json&limit=2"
                                    async with session.get(top_tracks_url) as track_resp:
                                        track_data = await track_resp.json()
                                        tracks = track_data.get("toptracks", {}).get("track", [])
                                        for t in tracks:
                                            title = f"{name} - {t['name']}"
                                            if title not in processed_tracks:
                                                similar_tracks.append(title)
                                                processed_tracks.add(title)
            except Exception as e:
                logging.error(f"Failed during tag-based enrichment: {e}")

        if not similar_tracks:
            await interaction.followup.send("⚠️ No tracks found. Try different tags or play a song first.", ephemeral=True)
            return

        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch1",
            "skip_download": True,
            "ignoreerrors": True,
            "cookiefile": "cookies.txt",
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }
        }

        async def queue_tracks(tracks):
            for track in tracks:
                try:
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(track, download=False)
                        video_info = info["entries"][0] if "entries" in info and info["entries"] else info
                        video_url = video_info.get("webpage_url")
                        if video_url:
                            await process_play(interaction, youtube_url=video_url)
                            logging.info(f"Queued: {track}")
                except Exception as e:
                    logging.error(f"Failed to queue {track}: {e}")
                await asyncio.sleep(1)

        if guild_id:
            old_task = self.bot.pandora_tasks.get(guild_id)
            if old_task and not old_task.done():
                old_task.cancel()
            task = asyncio.create_task(queue_tracks(similar_tracks))
            self.bot.pandora_tasks[guild_id] = task

        await interaction.followup.send(
            f"🎧 Pandora mode started!\nMood: {mood or 'None'}\nGenres: {genres or 'None'}\nSeed: {seed_artist or 'None'}\nQueued {len(similar_tracks)} tracks.",
            ephemeral=True
        )
        
    @commands.command(name='mp3_list_next')
    async def mp3_list_next(self, ctx):
        logging.debug("mp3_list_next command invoked")
        await process_mp3_list_next(ctx)

    @commands.command(name='mp3_list')
    async def mp3_list(self, ctx):
        logging.debug("mp3_list command invoked")
        await process_mp3_list(ctx)

async def setup_commands(bot):
    await bot.add_cog(MusicCommands(bot))
