# Discord Audio Bot

This Discord Audio Bot is a feature-rich bot designed to manage and play audio from various sources, including YouTube and MP3 files, directly in your Discord server. It includes a queue system to manage playback and interactive controls through both commands and buttons.

## Features

- Play audio from YouTube URLs, including playlists.
- Play audio from attached MP3 files.
- Manage a queue of audio tracks.
- Shuffle and reorder the queue.
- Loop the current track.
- Display a "Now Playing" message with interactive controls.
- Favorite tracks and display favorite status.
- Store and retrieve playback queues and last played audio state.

## Requirements

- Python 3.8 or higher
- Discord.py library
- yt-dlp library
- aiohttp library
- python-dotenv library

## Installation

1. Clone the repository or download the script.
2. Install the required Python libraries:

   ```sh
   pip install discord.py yt-dlp aiohttp python-dotenv
   ```

3. Create a `.env` file in the same directory as the script with your Discord bot token:

   ```
   discord_token=YOUR_DISCORD_BOT_TOKEN
   ```

4. Run the script:

   ```sh
   python your_script_name.py
   ```

## Usage

### Commands

- **/play [URL or attachment]**: Plays audio from a YouTube URL or an attached MP3 file. If a URL is provided, it can be a single video or a playlist. If an MP3 file is attached, it will be added to the queue and played if nothing is currently playing.

- **/mp3_list [URL or attachment]**: Similar to /play but works specifically for attached MP3 files including more than one MP3 file. Multiple MP3 files can be attached, and all will be added to the queue.

- **/play_video [title]**: Plays a specific video from the queue by its title.

- **/shuffle**: Randomly shuffles the current queue and shows the new order.

- **/list_queue**: Lists all entries currently in the queue.

- **/play_queue**: Starts playing the queue from the first track.

- **/remove_by_title [title]**: Removes a specific track by its title from the queue.

- **/skip**: Skips the current track and plays the next one in the queue.

- **/pause**: Pauses the currently playing track.

- **/resume**: Resumes playback if it is paused.

- **/stop**: Stops playback and disconnects the bot from the voice channel.

- **/restart**: Restarts the currently playing track from the beginning.

- **/remove_queue [index]**: Removes a track from the queue by its index.

- **/play_next [title]**: Moves a specified track to the second position in the queue.

- **/previous**: Plays the last entry that was being played.

- **/help**: Show the help text.

### Interactive Buttons

The bot provides several interactive buttons in the "Now Playing" embed message:

- **⏸️ Pause**: Pauses the currently playing track.
- **▶️ Resume**: Resumes playback if it is paused.
- **⏹️ Stop**: Stops playback and disconnects the bot from the voice channel.
- **⏭️ Skip**: Skips the current track and plays the next one in the queue.
- **🔄 Restart**: Restarts the currently playing track from the beginning.
- **🔀 Shuffle**: Randomly shuffles the current queue and shows the new order.
- **📜 List Queue**: Lists all entries currently in the queue.
- **❌ Remove**: Removes the current track from the queue.
- **⏮️ Previous**: Plays the last entry that was being played.
- **🔁 Loop**: Toggles looping of the current track.
- **⬆️ Move Up**: Moves the current track up one position in the queue.
- **⬇️ Move Down**: Moves the current track down one position in the queue.
- **⬆️⬆️ Move to Top**: Moves the current track to the top of the queue.
- **⬇️⬇️ Move to Bottom**: Moves the current track to the bottom of the queue.
- **⭐ Favorite / 💛 Favorited**: Toggles the favorite status of the current track.

## Code Overview

### `QueueEntry` Class

Represents a single audio entry in the queue. It includes methods to convert to and from dictionary format and to refresh the URL of the audio source.

### `BotQueue` Class

Manages the queue of audio entries. It includes methods to load and save the queue, add entries to the queue, and retrieve the current queue.

### `fetch_info` and `fetch_playlist_length` Functions

Fetch information about a video or playlist from YouTube using yt-dlp.

### `sanitize_filename` and `download_file` Functions

Sanitize filenames and download files from given URLs.

### `play_audio`, `send_now_playing`, `update_progress_bar`, and `play_next` Functions

Manage audio playback, send "Now Playing" messages, update progress bars, and play the next track in the queue.

### `AudioBot` Class

The main bot class that initializes the Discord bot and sets up commands.

### `ButtonView` Class

Defines the interactive buttons for controlling playback.

### `MusicCommands` Class

Defines the slash commands and other commands for managing playback and the queue.

### Running the Bot

The bot is started by running the `run_bot` function, which loads the bot token, sets up intents, and runs the bot.

## Notes

- Ensure the bot has permission to join and speak in voice channels.
- Make sure to configure your Discord application properly and add the bot to your server with the necessary permissions.
- The bot uses yt-dlp for YouTube extraction, which must be installed and accessible.

This bot provides a comprehensive set of features for managing and playing audio in your Discord server. Customize and extend the functionality as needed for your specific use case.

🎧 Popular Genre Tags on MusicBrainz:
These are reliable inputs under genres:

rock

pop

hip hop

electronic

jazz

metal

punk

r&b

country

reggae

classical

folk

blues

techno

house

trance

drum and bass

k-pop

j-pop

indie

alternative

🎵 Common Mood-Like Tags:
These are more freeform but still valid as mood input:

happy

chill

sad

dark

upbeat

mellow

aggressive

romantic

nostalgic

relaxing

energetic

moody

calm

melancholic

dreamy

ambient
