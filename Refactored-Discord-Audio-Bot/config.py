import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

GENIUS_API_TOKEN = os.getenv('genius_api_token')
DISCORD_TOKEN = os.getenv('discord_token')
MUSICBRAINZ_USER_AGENT = os.getenv("MUSICBRAINZ_USER_AGENT")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Other configuration settings
LOGGING_CONFIG = {
    'level': logging.DEBUG,
    'filename': 'bot.log',
    'format': '%(asctime)s:%(levelname)s:%(message)s'
}
