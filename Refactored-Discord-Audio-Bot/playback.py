import logging
import asyncio
import yt_dlp
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from discord import FFmpegPCMAudio, Interaction, PCMVolumeTransformer
from now_playing_helper import send_now_playing_message
from queue_manager import QueueEntry

logging.basicConfig(level=logging.DEBUG, filename='playback.log', format='%(asctime)s:%(levelname)s:%(message)s')

executor = ThreadPoolExecutor(max_workers=1)

class PlaybackManager:
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager

    async def play_audio(self, ctx_or_interaction, entry):
        try:
            server_id = str(ctx_or_interaction.guild.id)
            self.queue_manager.ensure_queue_exists(server_id)

            await self.refresh_url_if_needed(entry)
            entry.guild_id = str(ctx_or_interaction.guild.id)  # Ensure guild ID is set
            if entry.duration == 0:
                await self.update_entry_duration(entry)

            self.queue_manager.set_currently_playing(entry)
            self.queue_manager.is_paused = False

            self.queue_manager.save_queues()
            entry.start_time = datetime.now()
            entry.paused_duration = timedelta(0)

            logging.info(f"Starting playback for: {entry.title} (URL: {entry.best_audio_url})")
            print(f"Starting playback for: {entry.title} (URL: {entry.best_audio_url})")

            def after_playing_callback(error):
                self.handle_playback_end(ctx_or_interaction, entry, error)

            await self.start_playback(ctx_or_interaction, entry, after_playing_callback)
            logging.info("Calling send_now_playing")
            print("Calling send_now_playing")
            # Schedule a halfway point queue refresh
            halfway_duration = entry.duration / 2
            asyncio.create_task(self.schedule_halfway_queue_refresh(server_id, halfway_duration))
        except Exception as e:
            await self.handle_playback_exception(ctx_or_interaction, entry, e)

    async def schedule_halfway_queue_refresh(self, server_id, delay):
        await asyncio.sleep(delay)
        self.queue_manager.get_queue(server_id)
        logging.debug(f"Queue refreshed at halfway point for server {server_id}")
        print(f"Queue refreshed at halfway point for server {server_id}")
    
    def after_playing(self, ctx_or_interaction, entry):
        def after_playing_callback(error):
            self.queue_manager.stop_is_triggered = False
            if error:
                logging.error(f"Error playing {entry.title}: {error}")
                bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, Interaction) else ctx_or_interaction.bot
                asyncio.run_coroutine_threadsafe(ctx_or_interaction.channel.send("Error occurred during playback."), bot_client.loop).result()
            else:
                logging.info(f"Finished playing {entry.title} at {datetime.now()}")
                print(f"Finished playing {entry.title} at {datetime.now()}")
                self.manage_queue_after_playback(ctx_or_interaction, entry)
        return after_playing_callback

    def manage_queue_after_playback(self, ctx_or_interaction, entry):
        if not self.queue_manager.is_restarting and not self.queue_manager.has_been_shuffled and not self.queue_manager.loop:
            queue = self.queue_manager.get_queue(str(ctx_or_interaction.guild.id))
            logging.debug(f"Queue before managing playback: {[e.title for e in queue]}")
            if entry in queue:
                if entry.has_been_arranged and entry.has_been_played_after_arranged:
                    entry.has_been_arranged = False
                    entry.has_been_played_after_arranged = False
                    queue.remove(entry)
                    queue.append(entry)
                elif entry.has_been_arranged and not entry.has_been_played_after_arranged:
                    entry.has_been_played_after_arranged = True
                self.queue_manager.save_queues()
            logging.debug(f"Queue after managing playback: {[e.title for e in queue]}")
        if self.queue_manager.loop:
            logging.info(f"Looping {entry.title}")
            print(f"Looping {entry.title}")
            bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, Interaction) else ctx_or_interaction.bot
            asyncio.run_coroutine_threadsafe(self.play_audio(ctx_or_interaction, entry), bot_client.loop).result()
        else:
            if not self.queue_manager.is_restarting:
                self.queue_manager.last_played_audio[str(ctx_or_interaction.guild.id)] = entry.title
            self.queue_manager.save_queues()
            bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, Interaction) else ctx_or_interaction.bot
            asyncio.run_coroutine_threadsafe(self.play_next(ctx_or_interaction), bot_client.loop).result()
            
    def after_playing(self, ctx_or_interaction, entry):
        def after_playing_callback(error):
            self.queue_manager.stop_is_triggered = False
            if error:
                logging.error(f"Error playing {entry.title}: {error}")
                print(f"Error playing {entry.title}: {error}")
                bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, Interaction) else ctx_or_interaction.bot
                asyncio.run_coroutine_threadsafe(ctx_or_interaction.channel.send("Error occurred during playback."), bot_client.loop).result()
            else:
                logging.info(f"Finished playing {entry.title} at {datetime.now()}")
                print(f"Finished playing {entry.title} at {datetime.now()}")
                self.manage_queue_after_playback(ctx_or_interaction, entry)
        return after_playing_callback

    async def start_playback(self, ctx_or_interaction, entry, after_callback):
        try:
            logging.debug("Starting playback")
            print("Starting playback")
            voice_client = ctx_or_interaction.guild.voice_client
            if self.queue_manager.stop_is_triggered:
                logging.info("Playback stopped before starting")
                print("Playback stopped before starting")
                return

            if voice_client is None:
                logging.error("No voice client found.")
                print("No voice client found.")
                return

            audio_source = FFmpegPCMAudio(
                entry.best_audio_url,
                options='-bufsize 65536k -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -vn'
            )
            # Set volume to 50%
            audio_source = PCMVolumeTransformer(audio_source, volume=0.75)

            if not voice_client.is_playing():
                voice_client.play(audio_source, after=after_callback)
                print(f'setting currently playing entry - {entry.title} = entry.title')
                self.queue_manager.set_currently_playing(entry)
                asyncio.create_task(send_now_playing_message(ctx_or_interaction, entry))
                self.queue_manager.has_been_shuffled = False
                logging.info(f"Playback started for {entry.title} at {datetime.now()}")
                print(f"Playback started for {entry.title} at {datetime.now()}")
        except Exception as e:
            if not self.queue_manager.stop_is_triggered:
                logging.error(f"Exception during playback: {e}")
                print(f"Exception during playback: {e}")
                bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, Interaction) else ctx_or_interaction.bot
                await ctx_or_interaction.channel.send(f"An error occurred during playback: {e}")

    def handle_playback_end(self, ctx_or_interaction, entry, error):
        self.queue_manager.stop_is_triggered = False
        if error:
            logging.error(f"Error playing {entry.title}: {error}")
            print(f"Error playing {entry.title}: {error}")
            bot_client = ctx_or_interaction.client if isinstance(ctx_or_interaction, Interaction) else ctx_or_interaction.bot
            asyncio.run_coroutine_threadsafe(ctx_or_interaction.channel.send("Error occurred during playback."), bot_client.loop).result()
        else:
            logging.info(f"Finished playing {entry.title} at {datetime.now()}")
            print(f"Finished playing {entry.title} at {datetime.now()}")
            
            # Save the last played audio
            # server_id = str(ctx_or_interaction.guild.id)
            # queue_manager.last_played_audio[server_id] = entry.title
            # queue_manager.save_queues()
            
            self.manage_queue_after_playback(ctx_or_interaction, entry)

    async def play_next(self, interaction):
        logging.debug("Playing next track in the queue")
        print("Playing next track in the queue")
        server_id = str(interaction.guild.id)
        queue = self.queue_manager.get_queue(server_id)
        
        if queue and self.queue_manager.currently_playing:
            current_entry = self.queue_manager.currently_playing
            self.check_and_arrange_current_entry(queue, current_entry)
            
            self.queue_manager.is_restarting = False
            await self.play_next_entry_in_queue(interaction, queue)
            
    def check_and_arrange_current_entry(self, queue, current_entry):
        if current_entry in queue and not self.queue_manager.is_restarting:
            if not current_entry.has_been_arranged and not self.queue_manager.has_been_shuffled:
                queue.remove(current_entry)
                queue.append(current_entry)
            self.queue_manager.save_queues()
            
    async def play_next_entry_in_queue(self, interaction, queue):
        if queue:
            entry = queue[0]
            await self.play_audio(interaction, entry)

    async def handle_playback_exception(self, ctx_or_interaction, entry, exception):
        logging.error(f"Error in play_audio: {exception}")
        await ctx_or_interaction.followup.send(f"An error occurred: {exception}")

    async def fetch_info(self, url, index: int = None):
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
        
    def create_queue_entry(self, video_info, index):
        logging.debug(f"Creating QueueEntry from video_info: {video_info.get('title', 'Unknown title')}")
        print(f"Creating QueueEntry from video_info: {video_info.get('title', 'Unknown title')}")
        return QueueEntry(
            video_url=video_info.get('webpage_url', ''),
            best_audio_url=video_info.get('best_audio_url', ''),
            title=video_info.get('title', 'Unknown title'),
            is_playlist=True,
            thumbnail=video_info.get('thumbnail', ''),
            playlist_index=index,
            duration=video_info.get('duration', 0)
        )
        
    async def fetch_first_video_info(self, url):
        first_video_info = await self.fetch_info(url, index=1)
        if not first_video_info or 'entries' not in first_video_info or not first_video_info['entries']:
            return None
        return first_video_info['entries'][0]

    async def process_play_command(self, interaction, url):
        server_id = str(interaction.guild.id)
        first_video = await self.fetch_first_video_info(url)
        if not first_video:
            await interaction.followup.send("Could not retrieve the first video of the playlist.")
            return

        first_entry = self.create_queue_entry(first_video, 1)
        if not self.queue_manager.currently_playing:
            self.queue_manager.queues[server_id].insert(0, first_entry)
            await self.play_audio(interaction, first_entry)
        else:
            self.queue_manager.add_to_queue(server_id, first_entry)

        await interaction.followup.send(f"Added to queue: {first_entry.title}")

        if not self.queue_manager.currently_playing:
            await self.play_audio(interaction, first_entry)

        asyncio.create_task(self.process_rest_of_playlist(interaction, url, server_id))

    async def process_rest_of_playlist(self, interaction, url, server_id):
        playlist_length = await self.fetch_playlist_length(url)
        if playlist_length > 1:
            for index in range(2, playlist_length + 1):
                try:
                    info = await self.fetch_info(url, index=index)
                    if info and 'entries' in info and info['entries']:
                        video = info['entries'][0]
                        if video.get('is_unavailable', False):
                            logging.warning(f"Skipping unavailable video at index {index}")
                            await interaction.followup.send(f"Skipping unavailable video at index {index}")
                            continue
                        entry = self.create_queue_entry(video, index)
                        self.queue_manager.add_to_queue(server_id, entry)
                        await interaction.followup.send(f"Added to queue: {entry.title}")
                    else:
                        logging.warning(f"Skipping unavailable video at index {index}")
                        await interaction.followup.send(f"Skipping unavailable video at index {index}")
                except yt_dlp.utils.ExtractorError as e:
                    logging.warning(f"Skipping unavailable video at index {index}: {str(e)}")
                    await interaction.followup.send(f"Skipping unavailable video at index {index}")
                except Exception as e:
                    logging.error(f"Error processing video at index {index}: {str(e)}")
                    await interaction.followup.send(f"Error processing video at index {index}: {str(e)}")

        await self.send_queue_update(interaction, server_id)
        
    async def send_queue_update(self, interaction, server_id):
        queue = self.queue_manager.get_queue(server_id)
        titles = [entry.title for entry in queue]
        response = "Current Queue:\n" + "\n".join(f"{idx+1}. {title}" for idx, title in enumerate(titles))
        logging.debug(response)
        print(response)
        await interaction.followup.send(response)
    async def process_single_video_or_mp3(self, url, interaction):
        if url.lower().endswith('.mp3'):
            logging.debug(f"Processing MP3 file: {url}")
            print(f"Processing MP3 file: {url}")
            return QueueEntry(video_url=url, best_audio_url=url, title=url.split('/')[-1], is_playlist=False)
        else:
            video_info = await self.fetch_info(url)
            if video_info:
                logging.debug(f"Processing single video: {video_info.get('title', 'Unknown title')}")
                print(f"Processing single video: {video_info.get('title', 'Unknown title')}")
                return self.create_queue_entry(video_info, None)
            else:
                await interaction.response.send_message("Error retrieving video data.")
                logging.error("Error retrieving video data.")
                print("Error retrieving video data.")
                return None

    async def fetch_playlist_length(self, url):
        ydl_opts = {'quiet': True, 'noplaylist': False, 'extract_entries': True, 'ignoreerrors': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logging.debug(f"Fetching playlist length for URL: {url}")
                info = await asyncio.get_running_loop().run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
                length = len(info.get('entries', []))
                logging.info(f"Playlist length: {length}")
                return length
        except yt_dlp.utils.ExtractorError as e:
            logging.warning(f"Error fetching playlist length: {str(e)}")
            return 0

    async def refresh_url_if_needed(self, entry):
        if 'youtube.com' in entry.video_url or 'youtu.be' in entry.video_url:
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'ignoreerrors': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(entry.video_url, download=False)
                entry.best_audio_url = next((f['url'] for f in info['formats'] if f.get('acodec') != 'none'), entry.video_url)

    async def update_entry_duration(self, entry):
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'ignoreerrors': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(entry.video_url, download=False)
            entry.duration = info.get('duration', 0)
