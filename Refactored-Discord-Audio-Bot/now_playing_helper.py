from discord import Interaction, Embed
from queue_manager import QueueEntry, queue_manager
from utils import create_now_playing_embed, schedule_progress_bar_update, remove_orphaned_mp3_files
from button_view import ButtonView

async def send_now_playing_message(interaction: Interaction, entry: QueueEntry):
    await remove_orphaned_mp3_files(queue_manager)  # Add this line
    embed = create_now_playing_embed(entry)
    paused = interaction.guild.voice_client.is_paused() if interaction.guild.voice_client else False
    view = ButtonView(interaction.client, entry, paused=paused, current_user=interaction.user)
    message = await interaction.channel.send(embed=embed, view=view)
    await schedule_progress_bar_update(interaction, message, entry, ButtonView, queue_manager)
