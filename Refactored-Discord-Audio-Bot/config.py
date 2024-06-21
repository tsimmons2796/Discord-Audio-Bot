import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

GENIUS_API_TOKEN = os.getenv('genius_api_token')
DISCORD_TOKEN = os.getenv('discord_token')

# Other configuration settings
LOGGING_CONFIG = {
    'level': logging.DEBUG,
    'filename': 'bot.log',
    'format': '%(asctime)s:%(levelname)s:%(message)s'
}
