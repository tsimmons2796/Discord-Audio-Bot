import json
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from utils import sanitize_title

logging.basicConfig(level=logging.DEBUG, filename='queue_manager.log', format='%(asctime)s:%(levelname)s:%(message)s')

class QueueEntry:
    def __init__(self, video_url: str, best_audio_url: str, title: str, is_playlist: bool, thumbnail: str = '', playlist_index: Optional[int] = None, duration: int = 0, is_favorited: bool = False, favorited_by: Optional[List[Dict[str, str]]] = None, has_been_arranged: bool = False, has_been_played_after_arranged: bool = False, timestamp: Optional[str] = None, paused_duration: Optional[float] = 0.0, guild: Optional[str] = None):
        logging.debug(f"Creating QueueEntry: {title}, URL: {video_url}")
        print(f"Creating QueueEntry: {title}, URL: {video_url}, Guild: {guild}")
        self.video_url = video_url
        self.best_audio_url = best_audio_url
        self.title = sanitize_title(title)
        self.is_playlist = is_playlist
        self.playlist_index = playlist_index
        self.thumbnail = thumbnail
        self.duration = duration
        self.is_favorited = is_favorited
        self.favorited_by = favorited_by if favorited_by is not None else []
        self.has_been_arranged = has_been_arranged
        self.has_been_played_after_arranged = has_been_played_after_arranged
        self.timestamp = timestamp or datetime.now().isoformat()
        self.pause_start_time = None
        self.start_time = datetime.now()
        self.paused_duration = timedelta(seconds=paused_duration) if isinstance(paused_duration, (int, float)) else timedelta(seconds=0.0)
        self.guild = guild

    def to_dict(self):
        return self.__dict__

class BotQueue:
    def __init__(self):
        logging.debug("Initializing BotQueue")
        print("Initializing BotQueue")
        self.queues = self.load_queues()
        self.currently_playing = None
        self.queue_file = 'queue.json'  # Ensure this path is correct
        self.loop = False
        self.stop_is_triggered = False  # Added here
        self.is_restarting = False
        self.has_been_shuffled = False
        self.queue_cache = {}
        self.last_played_audio = self.load_last_played_audio()
        
    def validate_queue(self, server_id: str):
        logging.debug(f"Validating queue for server {server_id}")
        print(f"Validating queue for server {server_id}")
        if server_id not in self.queues:
            logging.error(f"No queue found for server {server_id}")
            print(f"No queue found for server {server_id}")
            return False
        for entry in self.queues[server_id]:
            if not isinstance(entry, QueueEntry):
                logging.error(f"Invalid queue entry detected: {entry}")
                print(f"Invalid queue entry detected: {entry}")
                return False
        logging.debug(f"Queue validation passed for server {server_id}")
        print(f"Queue validation passed for server {server_id}")
        return True

    def load_queues(self) -> Dict[str, List[QueueEntry]]:
        try:
            with open('queues.json', 'r') as file:
                queues_data = json.load(file)
                logging.info("Queues loaded successfully")
                print("Queues loaded successfully")
                return {server_id: [QueueEntry(**entry) for entry in entries] for server_id, entries in queues_data.items()}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Failed to load queues: {e}")
            print(f"Failed to load queues: {e}")
            return {}

    def save_queues(self):
        logging.debug("Saving queues to file")
        print("Saving queues to file")
        try:
            with open('queues.json', 'w') as file:
                json.dump({k: [entry.to_dict() for entry in v] for k, v in self.queues.items()}, file, indent=4)
                logging.info("Queues saved successfully")
                print("Queues saved successfully")
            with open('last_played_audio.json', 'w') as file:
                json.dump(self.last_played_audio, file, indent=4)
                logging.info("Last played audio saved successfully")
                print("Last played audio saved successfully")
            self.queue_cache = self.queues.copy()  # Update cache when saving
        except Exception as e:
            logging.error(f"Failed to save queues or last played audio: {e}")
            print(f"Failed to save queues or last played audio: {e}")
            # pass

    def get_queue(self, server_id: str) -> List[QueueEntry]:
        logging.debug(f"Getting queue for server: {server_id}")
        print(f"Getting queue for server: {server_id}")
        if server_id in self.queue_cache:
            return self.queue_cache[server_id]
        else:
            queue = self.queues.get(server_id, [])
            self.queue_cache[server_id] = queue
            return queue

    def log_queue_state(self, server_id: str, operation: str):
        if server_id in self.queues:
            logging.debug(f"Queue state {operation} for server {server_id}: {[entry.title for entry in self.queues[server_id]]}")
            print(f"Queue state {operation} for server {server_id}: {[entry.title for entry in self.queues[server_id]]}")
        else:
            logging.debug(f"No queue found for server {server_id} {operation}")
            print(f"No queue found for server {server_id} {operation}")


    def ensure_queue_exists(self, server_id: str):
        logging.debug(f"Ensuring queue exists for server: {server_id}")
        print(f"Ensuring queue exists for server: {server_id}")
        if server_id not in self.queues:
            self.queues[server_id] = []
            self.queue_cache[server_id] = self.queues[server_id]  # Update cache
            self.save_queues()
            logging.info(f"Ensured queue exists for server: {server_id}")
            print(f"Ensured queue exists for server: {server_id}")

    def add_to_queue(self, server_id: str, entry: QueueEntry):
        logging.debug(f"Adding {entry.title} to queue for server {server_id}")
        print(f"Adding {entry.title} to queue for server {server_id}")
        if server_id not in self.queues:
            self.queues[server_id] = []
        self.queues[server_id].append(entry)
        self.queue_cache[server_id] = self.queues[server_id]  # Update cache
        self.save_queues()
        self.log_queue_state(server_id, "after adding to queue")
        self.validate_queue(server_id)
        logging.info(f"Added {entry.title} to queue for server {server_id}")
        print(f"Added {entry.title} to queue for server {server_id}")

    def set_currently_playing(self, entry: Optional[QueueEntry]):
        self.currently_playing = entry
        
    def load_last_played_audio(self) -> Dict[str, Optional[str]]:
        logging.debug("Loading last played audio from file")
        print("Loading last played audio from file")
        try:
            with open('last_played_audio.json', 'r') as file:
                data = json.load(file)
                logging.info("Last played audio loaded successfully")
                print("Last played audio loaded successfully")
                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load last played audio: {e}")
            print(f"Failed to load last played audio: {e}")
            return {}
        
    def remove_from_queue(self, server_id: str, entry: QueueEntry):
        logging.debug(f"Removing {entry.title} from queue for server {server_id}")
        print(f"Removing {entry.title} from queue for server {server_id}")
        if server_id in self.queues:
            self.queues[server_id] = [e for e in self.queues[server_id] if e != entry]
            self.queue_cache[server_id] = self.queues[server_id]  # Update cache
            self.save_queues()
            self.log_queue_state(server_id, "after removing from queue")
            self.validate_queue(server_id)

            # Check if the removed entry is currently playing
            if self.currently_playing == entry:
                self.currently_playing = None
                # self.play_next_in_queue(server_id)

            logging.info(f"Removed {entry.title} from queue for server {server_id}")
            print(f"Removed {entry.title} from queue for server {server_id}")
            
    

# Initialize a single instance of BotQueue to be used in commands.py and playback_manager.py
queue_manager = BotQueue()
