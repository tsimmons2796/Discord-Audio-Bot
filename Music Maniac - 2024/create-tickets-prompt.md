I want to make a YouTube audio playing discord bot in python code using the libraries yt-dlp, ffmpeg and discord to be imported. The discord bot is already created and hooked up.

This is the starting area so far:
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

if **name** == "**main**":
run_bot()

We just need to flesh out the commands to be used.

For the commands I want:

- play
- skip
- pause
- resume
- stop
- previous
- list-queue
- clear-queue
- shuffle
- get-queue:<insert-queue-name>

Currently I want the code to handle any YouTube url (playlists and single videos)

I want there to be a clear queue. The data that is required for the audio for each video to be played in discord should be stored in the queue as their own entries along with the video title, if it is from a playlist or not, and if it is from a playlist then include it's index from that playlist. Leave room for more data to be added to each entry as I see fit for the future.

The queue should be written to a separate .json file and each queue should be started by the date. Whenever there is a new date then a new queue should be started. Each queue should have a specific name of some sort so you can use a command to get all of that data and then add it all to audio queue to be played.

This next section is for the commands being passed a single YouTube video:

The 'play' command should extract the data for the audio to be played and then added to the queue and then the queue should be played.

The 'skip' command should use the 'stop' command to stop the currently playing video if there is one then start playing the next video in the queue sequentially in numeric order of their index from the current queue. If there is no next video to be played in the queue then it should just stop playing any video audio.

The 'pause' command should just pause the current video audio being played if there is one being played.

The 'resume' command should start back playing the video audio where it was paused at.

The 'stop' command should restart the video audio being played currently if there is one and then pause it before any audio gets played.

The 'previous' command should stop the current video audio being played if there is one being played then start playing the video audio for the entry that was last played if there is one to be played. And by last played I mean in the order of index numerically 1 number before the current index of the entry being played.

The 'list-queue' command should print out all of the video titles and their indexes from the current queue if there are any to be printed out.

The 'clear-queue' command should remove all items from the current queue of the day.

The 'shuffle' command should re-order all of the entries in the queue. The index value of their position in the queue should not change. The index value of which index each entry that was in a playlist is a separate value and should not be changed regardless of their order in the queue for that day.

The 'get-queue:<insert-queue-name>' command should take a string value and get the queue that has that name value and start playing the audio for the first item in it if there is one.
