import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from commands import setup_commands
from events import setup_events
import nacl

# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')


def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=".", intents=intents)

    @client.event
    async def on_ready():
        logging.info(f'{client.user} is now connected and ready.')
    
    setup_commands(client)
    setup_events(client)
    client.run(TOKEN)

if __name__ == "__main__":
    run_bot()
