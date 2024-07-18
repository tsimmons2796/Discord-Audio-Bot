import logging
import os
import random
from datetime import datetime
import asyncio

from discord import Interaction, Embed, File, ButtonStyle
from queue_manager import queue_manager, QueueEntry
from utils import get_lyrics

logging.basicConfig(level=logging.DEBUG, filename='view_functions.log', format='%(asctime)s:%(levelname)s:%(message)s')


async def handle_lyrics_button(interaction: Interaction, entry: QueueEntry):
    logging.debug(f"Lyrics button clicked for: {entry.title}")
    await interaction.response.defer(ephemeral=True)

    lyrics = await get_lyrics(entry.title)

    if "Lyrics for " in lyrics:
        lyrics_filename = f"{entry.title.replace(' ', '_')}_lyrics.txt"
        with open(lyrics_filename, 'w', encoding='utf-8') as f:
            f.write(lyrics)
        file = File(lyrics_filename, filename=lyrics_filename)
        await interaction.followup.send(file=file)
        os.remove(lyrics_filename)
    else:
        await interaction.followup.send(lyrics)


async def handle_loop_button(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    logging.debug("Loop button callback triggered")

    if queue_manager.currently_playing:
        queue_manager.loop = not queue_manager.loop
        button_label = "🔁 Looped" if queue_manager.loop else "🔁 Loop"
        button_style = ButtonStyle.primary if queue_manager.loop else ButtonStyle.secondary
        await interaction.followup.send(f"Looping {'enabled' if queue_manager.loop else 'disabled'}.")
        logging.info(f"Looping {'enabled' if queue_manager.loop else 'disabled'} for {queue_manager.currently_playing.title}")
        await update_now_playing(interaction, queue_manager.currently_playing, button_label, button_style)
    else:
        await interaction.followup.send("No track is currently playing.", ephemeral=True)


async def handle_favorite_button(interaction: Interaction, entry: QueueEntry, current_user):
    logging.debug("Favorite button callback triggered")
    await interaction.response.defer(ephemeral=True)
    user_id = interaction.user.id
    user_name = interaction.user.display_name
    if user_id in [user['id'] for user in entry.favorited_by]:
        entry.favorited_by = [user for user in entry.favorited_by if user['id'] != user_id]
        entry.is_favorited = False
        button_style = ButtonStyle.secondary
        button_label = "⭐ Favorite"
    else:
        entry.favorited_by.append({'id': user_id, 'name': user_name})
        entry.is_favorited = True
        button_style = ButtonStyle.primary
        button_label = "💛 Favorited"

    queue_manager.save_queues()
    await update_now_playing(interaction, entry, button_label, button_style)


async def handle_pause_button(interaction: Interaction, entry: QueueEntry, button_view):
    await interaction.response.defer(ephemeral=True)
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        queue_manager.is_paused = True
        entry.pause_start_time = datetime.now()
        button_view.paused = True
        logging.debug(f"Pause button clicked. Setting paused to {button_view.paused}")
        button_view.update_buttons()
        await interaction.message.edit(view=button_view)
        await interaction.followup.send('Playback paused.', ephemeral=True)
        # Stop the progress update task
        if button_view.progress_update_task:
            button_view.progress_update_task.cancel()
            button_view.progress_update_task = None


async def handle_resume_button(interaction: Interaction, entry: QueueEntry, button_view):
    await interaction.response.defer(ephemeral=True)
    if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        queue_manager.is_paused = False
        entry.paused_duration += datetime.now() - entry.pause_start_time
        entry.pause_start_time = None
        button_view.paused = False
        logging.debug(f"Resume button clicked. Setting paused to {button_view.paused}")
        button_view.update_buttons()
        await interaction.message.edit(view=button_view)
        await interaction.followup.send('Playback resumed.', ephemeral=True)
        await button_view.start_progress_update_task(interaction, entry)  # Restart the progress update task


async def handle_stop_button(interaction: Interaction):
    await interaction.response.defer()  # Defer the response
    if interaction.guild.voice_client:
        queue_manager.stop_is_triggered = True
        queue_manager.currently_playing = None
        try:
            interaction.guild.voice_client.stop()
        except Exception as e:
            logging.error(f"Error stopping the voice client: {e}")
        await interaction.guild.voice_client.disconnect()
        await interaction.followup.send('Playback stopped and disconnected.', ephemeral=True)


async def handle_skip_button(interaction: Interaction):
    await interaction.response.defer()  # Defer the response
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    if not queue:
        await interaction.followup.send("Queue is empty.", ephemeral=True)
        return

    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await asyncio.sleep(0.5)
        await interaction.followup.send("Skipped the current track.", ephemeral=True)
    else:
        await interaction.followup.send("Nothing is currently playing.", ephemeral=True)


async def handle_restart_button(interaction: Interaction, button_view):
    await interaction.response.defer()  # Defer the response
    if not queue_manager.currently_playing:
        await interaction.followup.send("No track is currently playing.", ephemeral=True)
        return

    current_entry = queue_manager.currently_playing
    queue_manager.is_restarting = True

    if interaction.guild.voice_client:
        interaction.guild.voice_client.stop()
        await asyncio.sleep(0.5)
        await button_view.playback_manager.play_audio(interaction, current_entry)


async def handle_shuffle_button(interaction: Interaction, button_view):
    await interaction.response.defer()  # Defer the response
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    if not queue:
        await interaction.followup.send("The queue is currently empty.")
        return
    first_entry_before_shuffle = queue_manager.currently_playing

    queue_manager.has_been_shuffled = True
    random.shuffle(queue)
    for entry in queue:
        entry.has_been_arranged = False
    queue_manager.queues[server_id] = queue
    queue_manager.save_queues()

    await display_queue(interaction, "Queue after shuffle", queue)

    if first_entry_before_shuffle or any(vc.is_paused() for vc in interaction.guild.voice_client):
        await button_view.send_now_playing_for_buttons(interaction, first_entry_before_shuffle)


async def handle_list_queue_button(interaction: Interaction, button_view):
    await interaction.response.defer()  # Defer the response
    server_id = str(interaction.guild.id)
    queue_manager.ensure_queue_exists(server_id)
    queue = queue_manager.get_queue(server_id)
    if not queue:
        await interaction.followup.send("The queue is currently empty.")
    else:
        await display_queue(interaction, "Current Queue", queue)

        if queue_manager.currently_playing:
            await button_view.send_now_playing_for_buttons(interaction, queue_manager.currently_playing)


async def handle_remove_button(interaction: Interaction):
    await interaction.response.defer()  # Defer the response
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    # Access the entry directly from the interaction's view
    entry = interaction.view.entry
    if entry in queue:
        queue.remove(entry)
        queue_manager.save_queues()
        await interaction.followup.send(f"Removed '{entry.title}' from the queue.", ephemeral=True)

    # Check if the entry is currently playing and stop it if necessary
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing() and queue_manager.currently_playing == entry:
        interaction.guild.voice_client.stop()
        queue_manager.currently_playing = None
        await interaction.followup.send(f"Stopped playback and removed '{entry.title}' from the queue.", ephemeral=True)


async def handle_previous_button(interaction: Interaction):
    await interaction.response.defer()  # Defer the response

    server_id = str(interaction.guild.id)
    last_played = queue_manager.last_played_audio.get(server_id)
    if not last_played:
        await interaction.followup.send("There was nothing played prior.", ephemeral=True)
        return

    queue = queue_manager.get_queue(server_id)
    entry = next((e for e in queue if e.title == last_played), None)

    if not entry:
        await interaction.followup.send("No previously played track found.", ephemeral=True)
        return

    queue.remove(entry)
    queue.insert(1, entry)
    queue_manager.save_queues()
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await asyncio.sleep(0.5)
        await interaction.message.view.playback_manager.play_audio(interaction, entry)
        await interaction.message.view.refresh_view(interaction)


async def handle_move_up_button(interaction: Interaction, entry: QueueEntry):
    await interaction.response.defer()  # Defer the response
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    entry_index = queue.index(entry)

    if entry_index > 0:
        queue.insert(entry_index - 1, queue.pop(entry_index))
        entry.has_been_arranged = True
        queue_manager.save_queues()
        await interaction.followup.send(f"Moved '{entry.title}' up in the queue.", ephemeral=True)
        await interaction.message.view.refresh_view(interaction)
    else:
        await interaction.followup.send(f"'{entry.title}' is already at the top of the queue.", ephemeral=True)


async def handle_move_down_button(interaction: Interaction, entry: QueueEntry):
    await interaction.response.defer()  # Defer the response
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    entry_index = queue.index(entry)

    if entry_index < len(queue) - 1:
        queue.insert(entry_index + 1, queue.pop(entry_index))
        entry.has_been_arranged = True
        queue_manager.save_queues()
        await interaction.followup.send(f"Moved '{entry.title}' down in the queue.", ephemeral=True)
        await interaction.message.view.refresh_view(interaction)
    else:
        await interaction.followup.send(f"'{entry.title}' is already at the bottom of the queue.", ephemeral=True)


async def handle_move_to_top_button(interaction: Interaction, entry: QueueEntry):
    await interaction.response.defer()  # Defer the response
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    entry_index = queue.index(entry)

    if entry_index > 0:
        queue.insert(0, queue.pop(entry_index))
        entry.has_been_arranged = True
        queue_manager.save_queues()
        await interaction.followup.send(f"Moved '{entry.title}' to the top of the queue.", ephemeral=True)
        await interaction.message.view.refresh_view(interaction)
    else:
        await interaction.followup.send(f"'{entry.title}' is already at the top of the queue.", ephemeral=True)


async def handle_move_to_bottom_button(interaction: Interaction, entry: QueueEntry):
    await interaction.response.defer()  # Defer the response
    server_id = str(interaction.guild.id)
    queue = queue_manager.get_queue(server_id)
    entry_index = queue.index(entry)

    if entry_index < len(queue) - 1:
        queue.append(queue.pop(entry_index))
        entry.has_been_arranged = True
        queue_manager.save_queues()
        await interaction.followup.send(f"Moved '{entry.title}' to the bottom of the queue.", ephemeral=True)
        await interaction.message.view.refresh_view(interaction)
    else:
        await interaction.followup.send(f"'{entry.title}' is already at the bottom of the queue.", ephemeral=True)


async def update_now_playing(interaction: Interaction, entry: QueueEntry, button_label: str, button_style):
    embed = interaction.message.embeds[0]
    favorited_by = ', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else "No one"
    embed.set_field_at(0, name="Favorited by", value=favorited_by, inline=False)
    interaction.message.view.favorite_button.label = button_label
    interaction.message.view.favorite_button.style = button_style
    await interaction.message.edit(embed=embed, view=interaction.message.view)


async def display_queue(interaction: Interaction, title: str, queue):
    def format_duration(seconds):
        mins, secs = divmod(seconds, 60)
        return f"{mins}:{secs:02d}"

    def create_embed(title, description, fields):
        embed = Embed(title=title, description=description)
        for field in fields:
            embed.add_field(name=field["name"], value=field["description"], inline=False)
        return embed

    fields = []
    for idx, entry in enumerate(queue):
        field_name = f"{idx + 1}. {entry.title}"
        if "youtube.com" in entry.video_url or "youtu.be" in entry.video_url:
            field_value = (
                f"**URL:** [Link]({entry.video_url})\n"
                f"**Duration:** {format_duration(entry.duration)}\n"
                f"**Favorited by:** {', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else 'No one'}"
            )
        else:
            field_value = (
                f"**Duration:** {format_duration(entry.duration)}\n"
                f"**Favorited by:** {', '.join([user['name'] for user in entry.favorited_by]) if entry.favorited_by else 'No one'}"
            )
        fields.append({"name": field_name, "description": field_value})

    max_fields_per_embed = 25
    queue_embeds = []
    for i in range(0, len(fields), max_fields_per_embed):
        embed_fields = fields[i:i + max_fields_per_embed]
        embed = create_embed(title, f"Listing entries {i + 1} - {i + len(embed_fields)}", embed_fields)
        queue_embeds.append(embed)

    for embed in queue_embeds:
        await interaction.followup.send(embed=embed)
