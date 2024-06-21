import logging
from discord.ext import commands
from config import DISCORD_TOKEN
from commands import setup_commands
from queue_manager import BotQueue, QueueEntry
from views import ButtonView
from discord import Intents

logging.basicConfig(level=logging.DEBUG, filename='bot.log', format='%(asctime)s:%(levelname)s:%(message)s')

class AudioBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        logging.debug("Initializing AudioBot")
        super().__init__(command_prefix, intents=intents)
        self.queue_manager = BotQueue()
        self.message_views = {}
        self.now_playing_messages = []

    async def setup_hook(self):
        logging.debug("Setting up hook for AudioBot")
        dummy_entry = QueueEntry(video_url='', best_audio_url='', title='dummy', is_playlist=False, guild=None)
        self.add_view(ButtonView(self, dummy_entry))
        await setup_commands(self)
        await self.tree.sync()

    async def on_ready(self):
        logging.info(f'{self.user} is now connected and ready.')
        print(f'{self.user} is now connected and ready.')

    async def on_message(self, message):
        view = self.message_views.get(message.id)
        if view:
            await message.edit(view=view)
        
        # Check for mp3_list command trigger
        if message.content.startswith(".mp3_list"):
            ctx = await self.get_context(message)
            await self.invoke(ctx)

        # Check for listen command trigger
        if message.content.startswith("!listen"):
            ctx = await self.get_context(message)
            await self.invoke(ctx)

    def add_now_playing_message(self, message_id):
        self.now_playing_messages.append(message_id)

    def clear_now_playing_messages(self):
        self.now_playing_messages.clear()

if __name__ == '__main__':
    intents = Intents.default()
    intents.voice_states = True
    intents.message_content = True

    bot = AudioBot(command_prefix="!", intents=intents)
    bot.run(DISCORD_TOKEN)
