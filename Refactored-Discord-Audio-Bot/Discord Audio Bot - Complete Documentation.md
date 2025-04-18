# Discord Audio Bot - Complete Documentation

This comprehensive documentation provides detailed instructions for installing, configuring, and using the Discord Audio Bot. It covers everything from installation requirements to command usage and internal functionality.

## Table of Contents

1. [Installation Guide](#installation-guide)
   - [Prerequisites](#prerequisites)
   - [Setting Up the Environment](#setting-up-the-environment)
   - [Installing FFmpeg](#installing-ffmpeg)
   - [Installing Python Dependencies](#installing-python-dependencies)
   - [Configuration Setup](#configuration-setup)
   - [Verification and Troubleshooting](#verification-and-troubleshooting)

2. [User Guide](#user-guide)
   - [Slash Commands](#slash-commands)
   - [Button Interface](#button-interface)
   - [Now Playing Display](#now-playing-display)
   - [Interaction Flow](#interaction-flow)
   - [Special Features](#special-features)

3. [Developer Guide](#developer-guide)
   - [Project Structure](#project-structure)
   - [Core Components](#core-components)
   - [Logic Flow](#logic-flow)
   - [Extending the Bot](#extending-the-bot)

---

# Installation Guide

## Prerequisites

Before installing the bot, ensure you have the following prerequisites:

- Python 3.8 or higher
- pip (Python package installer)
- Git (for cloning the repository)
- Administrative privileges (for system-wide installations)

## Setting Up the Environment

1. **Clone the Repository**

```bash
git clone https://github.com/your-username/Refactored-Discord-Audio-Bot.git
cd Refactored-Discord-Audio-Bot
```

2. **Set Up a Virtual Environment (Recommended)**

Creating a virtual environment is recommended to avoid conflicts with other Python projects:

### For Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### For macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

## Installing FFmpeg

FFmpeg is required for audio processing and playback functionality.

### For Windows:

1. Download FFmpeg from the official website: https://ffmpeg.org/download.html
   - Choose the Windows build by BtbN (https://github.com/BtbN/FFmpeg-Builds/releases)
   - Download the latest `ffmpeg-master-latest-win64-gpl.zip`

2. Extract the ZIP file to a location on your computer (e.g., `C:\ffmpeg`)

3. Add FFmpeg to your system PATH:
   - Right-click on "This PC" or "My Computer" and select "Properties"
   - Click on "Advanced system settings"
   - Click on "Environment Variables"
   - Under "System variables", find and select the "Path" variable, then click "Edit"
   - Click "New" and add the path to the FFmpeg bin directory (e.g., `C:\ffmpeg\bin`)
   - Click "OK" to close all dialogs

4. Verify the installation by opening a new Command Prompt and typing:
   ```bash
   ffmpeg -version
   ```

### For macOS (using Homebrew):

```bash
brew install ffmpeg
```

### For Ubuntu/Debian Linux:

```bash
sudo apt update
sudo apt install ffmpeg
```

### For Fedora/RHEL/CentOS:

```bash
sudo dnf install ffmpeg ffmpeg-devel
```

## Installing Python Dependencies

The bot requires several Python packages to function properly. Install them using pip:

```bash
pip install -r requirements.txt
```

If a `requirements.txt` file is not provided, install the following packages manually:

```bash
pip install discord.py[voice] python-dotenv yt-dlp aiohttp mutagen lyricsgenius
```

### Detailed Package Information:

1. **discord.py[voice]**: Discord API wrapper with voice support
   - Version: Latest (2.0.0+)
   - Purpose: Core functionality for Discord bot interactions and voice capabilities

2. **python-dotenv**: Environment variable management
   - Version: Latest
   - Purpose: Loads environment variables from .env files for secure configuration

3. **yt-dlp**: YouTube downloader and extractor
   - Version: Latest
   - Purpose: Handles YouTube video/audio extraction and downloading

4. **aiohttp**: Asynchronous HTTP client/server
   - Version: Latest
   - Purpose: Handles asynchronous HTTP requests for API interactions

5. **mutagen**: Audio metadata handling
   - Version: Latest
   - Purpose: Extracts and processes metadata from audio files

6. **lyricsgenius**: Genius API wrapper
   - Version: Latest
   - Purpose: Fetches song lyrics from Genius

## Configuration Setup

1. Create a `.env` file in the root directory of the project with the following variables:

```
discord_token=YOUR_DISCORD_BOT_TOKEN
genius_api_token=YOUR_GENIUS_API_TOKEN
MUSICBRAINZ_USER_AGENT=YOUR_APP_NAME/1.0 (YOUR_CONTACT_EMAIL)
LASTFM_API_KEY=YOUR_LASTFM_API_KEY
```

2. Replace the placeholder values with your actual API keys:
   - `YOUR_DISCORD_BOT_TOKEN`: Obtain from the [Discord Developer Portal](https://discord.com/developers/applications)
   - `YOUR_GENIUS_API_TOKEN`: Obtain from the [Genius API](https://genius.com/api-clients)
   - `YOUR_APP_NAME` and `YOUR_CONTACT_EMAIL`: Your application name and contact email for MusicBrainz API
   - `YOUR_LASTFM_API_KEY`: Obtain from the [Last.fm API](https://www.last.fm/api)

### Creating a Discord Bot and Getting a Token:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Navigate to the "Bot" tab and click "Add Bot"
4. Under the "TOKEN" section, click "Copy" to copy your bot token
5. Enable the following Privileged Gateway Intents:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent

### Bot Permissions:

When adding the bot to your server, ensure it has the following permissions:
- Read Messages/View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Add Reactions
- Connect to Voice Channels
- Speak in Voice Channels
- Use Application Commands

## Verification and Troubleshooting

To verify that all dependencies are correctly installed, run the test script:

```bash
python test.py
```

If everything is set up correctly, you should see a success message.

### FFmpeg Issues:

1. **FFmpeg not found error**:
   - Ensure FFmpeg is properly installed and added to your system PATH
   - Try reinstalling FFmpeg following the instructions above
   - For Windows users, restart your computer after adding FFmpeg to PATH

2. **Audio playback issues**:
   - Make sure you have the latest version of FFmpeg installed
   - Check that your Discord bot has proper permissions in the voice channel

### Python Package Issues:

1. **Discord.py voice support not working**:
   - Ensure you've installed discord.py with voice support: `pip install discord.py[voice]`
   - On Linux, you might need additional packages: `sudo apt install libffi-dev libnacl-dev python3-dev`

2. **yt-dlp errors**:
   - Update yt-dlp to the latest version: `pip install -U yt-dlp`
   - If you encounter "HTTP Error 429: Too Many Requests", it means you're being rate-limited by YouTube

### Environment Variable Issues:

1. **Bot not connecting to Discord**:
   - Verify your Discord token is correct and properly set in the .env file
   - Ensure the .env file is in the root directory of the project

2. **API functionality not working**:
   - Check that all API keys are correctly set in the .env file
   - Verify that the APIs you're using haven't changed their authentication methods

---

# User Guide

## Slash Commands

The bot provides the following slash commands for controlling audio playback and queue management:

### Playback Controls

1. `/play` - Play a YouTube URL, YouTube title, or MP3 file
   - Parameters:
     - `youtube_url` (optional): Direct YouTube video or playlist URL
     - `youtube_title` (optional): Title to search on YouTube
     - `mp3_file` (optional): MP3 file attachment to play
   - Behavior: If no audio is playing, starts playback immediately; otherwise adds to the end of the queue

2. `/play_next_in_queue` - Add a track to play immediately after the current one
   - Parameters:
     - `youtube_url` (optional): Direct YouTube video or playlist URL
     - `youtube_title` (optional): Title to search on YouTube
     - `mp3_file` (optional): MP3 file attachment to play
   - Behavior: Adds the track to the second position in the queue (right after the currently playing track)

3. `/pause` - Pause the currently playing track
   - Behavior: Pauses playback and records the pause time for accurate progress tracking

4. `/resume` - Resume playback if it is paused
   - Behavior: Resumes playback and calculates the total paused duration for accurate progress tracking

5. `/stop` - Stop playback and disconnect the bot from the voice channel
   - Behavior: Stops playback, clears the currently playing track, and disconnects from voice

6. `/skip` - Skip the current track
   - Behavior: Stops the current track and begins playing the next track in the queue

7. `/restart` - Restart the currently playing track from the beginning
   - Behavior: Stops and replays the current track from the beginning

8. `/previous` - Play the last entry that was being played
   - Behavior: Retrieves the last played track and plays it again

### Queue Management

9. `/play_queue` - Play the current queue
   - Behavior: Starts playback of the queue from the beginning

10. `/list_queue` - List all entries in the current queue
    - Behavior: Displays an embed with all tracks in the queue, including titles, durations, and favorite status

11. `/remove_queue` - Remove a track from the queue by index
    - Parameters:
      - `index`: The position number of the track to remove
    - Behavior: Removes the specified track from the queue

12. `/remove_by_title` - Remove a track from the queue by title
    - Parameters:
      - `title`: The title of the track to remove
    - Behavior: Removes the specified track from the queue

13. `/clear_queue` - Clear the queue except the currently playing entry
    - Behavior: Removes all tracks from the queue except the one currently playing

14. `/shuffle` - Shuffle the current queue
    - Behavior: Randomly reorders all tracks in the queue

15. `/move_to_next` - Move a specified track to play next
    - Parameters:
      - `title`: The title of the track to move (with autocomplete)
    - Behavior: Moves the specified track to the second position in the queue

16. `/search_and_play_from_queue` - Search the queue and play a specific track
    - Parameters:
      - `title`: The title to search for (with autocomplete)
    - Behavior: Finds the matching track in the queue and plays it immediately

17. `/remove_duplicates` - Remove duplicate songs from the queue based on title
    - Behavior: Identifies and removes tracks with duplicate titles, keeping only one instance

### Discovery Features

18. `/discover` - Play music by mood, genre, or similar to current song
    - Parameters:
      - `mood` (optional): Mood of the music (e.g., happy, chill, sad)
      - `genres` (optional): Genres separated by commas (e.g., rock, electronic, jazz)
    - Behavior: Uses LastFM API to find and queue tracks matching the specified mood/genres or similar to the currently playing track

### Help and Information

19. `/help` - Show the help text
    - Behavior: Displays information about available commands and how to use them

### Legacy Text Commands

The bot also supports these legacy text commands:

1. `.mp3_list` - List available MP3 files
   - Behavior: Shows a list of MP3 files in the downloaded-mp3s directory

2. `.mp3_list_next` - List the next page of MP3 files
   - Behavior: Shows the next page of MP3 files if the list is too long

3. `.listen` - Voice listening command (details not fully specified in the code)

## Button Interface

During playback, the bot displays an interactive message with buttons for controlling the current track and queue. These buttons provide a user-friendly way to control playback without typing commands.

### Playback Control Buttons

1. **⏸️ Pause** - Pause the currently playing track
   - Changes to "▶️ Resume" when paused

2. **▶️ Resume** - Resume playback when paused
   - Only visible when playback is paused

3. **⏹️ Stop** - Stop playback and disconnect the bot

4. **⏭️ Skip** - Skip to the next track in the queue

5. **🔄 Restart** - Restart the current track from the beginning

6. **⏮️ Previous** - Play the previously played track

7. **🔁 Loop** - Toggle loop mode for the current track
   - Changes to "🔁 Looped" when active
   - Style changes to indicate active state

### Queue Management Buttons

8. **🔀 Shuffle** - Shuffle the current queue

9. **📜 List Queue** - Display all tracks in the current queue

10. **❌ Remove** - Remove the current track from the queue

11. **⬆️ Move Up** - Move the current track up one position in the queue
    - Only visible if the track is not at the top of the queue

12. **⬇️ Move Down** - Move the current track down one position in the queue
    - Only visible if the track is not at the bottom of the queue

13. **⬆️⬆️ Move to Top** - Move the current track to the top of the queue
    - Only visible if the track is not already at the top

14. **⬇️⬇️ Move to Bottom** - Move the current track to the bottom of the queue
    - Only visible if the track is not already at the bottom

### Additional Feature Buttons

15. **⭐ Favorite** - Mark the current track as a favorite
    - Changes to "💛 Favorited" when favorited by the current user
    - Style changes to indicate favorited state

16. **Lyrics** - Display lyrics for the current track
    - Fetches lyrics using the Genius API
    - Sends lyrics as text or as a file if they're too long

## Now Playing Display

During playback, the bot displays a "Now Playing" embed with detailed information about the current track:

### Embed Content

1. **Title**: "Now Playing"

2. **Description**: The title of the current track

3. **URL**: Link to the YouTube video (if applicable)

4. **Thumbnail**: Thumbnail image of the video or track

5. **Fields**:
   - **Favorited by**: List of users who have favorited this track
   - **Progress**: Visual progress bar showing playback position
     - Format: `[====== ]` (proportional to current position)
     - Time indicators: `0:45 / 3:21` (current time / total duration)

### Progress Bar Updates

- The progress bar updates automatically every 2 seconds during playback
- Updates pause when playback is paused
- Accurately accounts for paused time when calculating progress

## Interaction Flow

### Playing a Track

1. User invokes `/play` with a YouTube URL, title, or MP3 file
2. Bot responds with "Added to queue" message
3. If no track is currently playing, bot:
   - Joins the user's voice channel
   - Starts playback immediately
   - Displays the "Now Playing" embed with interactive buttons
4. If a track is already playing, the new track is added to the end of the queue

### Queue Management

1. User can view the queue using `/list_queue` or the "📜 List Queue" button
2. Queue is displayed as an embed with numbered entries
3. Each entry shows:
   - Title
   - URL (if from YouTube)
   - Duration
   - Users who have favorited it
4. Users can modify the queue using commands or buttons:
   - Remove tracks
   - Reorder tracks
   - Shuffle the queue
   - Clear the queue

### Playback Control

1. During playback, users can:
   - Pause/resume using buttons or commands
   - Skip to the next track
   - Restart the current track
   - Stop playback completely
2. The "Now Playing" embed updates to reflect the current state
3. Progress bar updates in real-time

### Favoriting Tracks

1. User clicks the "⭐ Favorite" button
2. Bot adds the user to the track's favorited_by list
3. Button changes to "💛 Favorited" with updated style
4. "Favorited by" field in the embed updates to include the user's name
5. Favorited status persists across sessions

### Lyrics Display

1. User clicks the "Lyrics" button
2. Bot searches for lyrics using the Genius API
3. If lyrics are found:
   - Short lyrics are sent directly in the channel
   - Long lyrics are saved to a file and attached
4. If lyrics aren't found, an error message is displayed

## Special Features

### Playlist Handling

- When a YouTube playlist URL is provided, the bot:
  1. Adds the first video to the queue immediately
  2. Processes the rest of the playlist in the background
  3. Sends messages as each track is added to the queue

### MP3 File Support

- Users can upload MP3 files directly to Discord
- The bot extracts metadata (title, artist, duration) from the file
- MP3 files are stored in the downloaded-mp3s directory for future use

### Music Discovery

- The `/discover` command uses LastFM API to find music based on:
  1. Mood (happy, chill, sad, etc.)
  2. Genres (rock, electronic, jazz, etc.)
  3. Similarity to the currently playing track
- Discovered tracks are automatically added to the queue

### Autocomplete Support

- Commands that require a track title (`/move_to_next`, `/search_and_play_from_queue`) provide autocomplete suggestions based on the current queue
- Suggestions update as the user types, showing up to 25 matching tracks

---

# Developer Guide

## Project Structure

The Discord Audio Bot is organized into several Python modules, each handling specific functionality:

### Core Files

- **bot.py**: Main entry point that initializes the bot and sets up event handlers
- **config.py**: Configuration settings and environment variable loading
- **commands.py**: Defines all slash commands and their parameters
- **command_functions.py**: Implements the logic for each command
- **button_view.py**: Defines the interactive button interface
- **view_functions.py**: Implements the logic for button interactions
- **playback.py**: Handles audio playback and streaming
- **queue_manager.py**: Manages the audio queue and persistence
- **utils.py**: Utility functions for various operations
- **now_playing_helper.py**: Helper functions for the "Now Playing" display

### Data Files

- **queues.json**: Persistent storage for queue state
- **last_played_audio.json**: Tracks the last played audio for each server
- **downloaded-mp3s/**: Directory for storing uploaded MP3 files

## Core Components

### AudioBot Class (bot.py)

The `AudioBot` class extends Discord's `commands.Bot` and serves as the main entry point:

```python
class AudioBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix, intents=intents, help_command=None)
        self.queue_manager = BotQueue()
        self.message_views = {}
        self.now_playing_messages = []
```

Key methods:
- `setup_hook()`: Initializes the bot and registers commands
- `on_ready()`: Handles bot startup events
- `on_message()`: Processes legacy text commands
- `on_voice_state_update()`: Manages voice channel events

### Queue Management (queue_manager.py)

The `BotQueue` class manages audio queues for each server:

```python
class BotQueue:
    def __init__(self):
        self.queues = {}
        self.last_played_audio = {}
        self.currently_playing = None
        self.is_paused = False
        self.loop = False
        self.is_restarting = False
        self.stop_is_triggered = False
        self.has_been_shuffled = False
        self.load_queues()
```

Key methods:
- `get_queue(server_id)`: Retrieves the queue for a specific server
- `add_to_queue(server_id, entry)`: Adds an entry to a server's queue
- `set_currently_playing(entry)`: Updates the currently playing track
- `save_queues()`: Persists queue state to disk

### QueueEntry Class (queue_manager.py)

The `QueueEntry` class represents a single track in the queue:

```python
class QueueEntry:
    def __init__(self, video_url, best_audio_url, title, is_playlist=False, guild_id=None, thumbnail='', playlist_index=0, duration=0):
        self.video_url = video_url
        self.best_audio_url = best_audio_url
        self.title = title
        self.is_playlist = is_playlist
        self.guild_id = guild_id
        self.thumbnail = thumbnail
        self.playlist_index = playlist_index
        self.duration = duration
        self.favorited_by = []
        self.is_favorited = False
        self.has_been_arranged = False
        self.has_been_played_after_arranged = False
        self.start_time = None
        self.pause_start_time = None
        self.paused_duration = timedelta(0)
```

### PlaybackManager Class (playback.py)

The `PlaybackManager` class handles audio playback:

```python
class PlaybackManager:
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager
```

Key methods:
- `play_audio(ctx_or_interaction, entry)`: Plays an audio track
- `start_playback(ctx_or_interaction, entry, after_callback)`: Starts the actual playback
- `play_next(interaction)`: Plays the next track in the queue
- `fetch_info(url, index)`: Fetches information about a YouTube video or playlist

### ButtonView Class (button_view.py)

The `ButtonView` class creates the interactive button interface:

```python
class ButtonView(View):
    def __init__(self, bot, entry: QueueEntry, paused: bool = False, current_user: Optional[User] = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.paused = paused
        self.entry = entry
        self.current_user = current_user
        # Button initialization...
```

Key methods:
- `update_buttons()`: Updates the button state based on current playback
- `refresh_view(interaction)`: Refreshes the view after button interactions
- Various button callback methods for handling user interactions

## Logic Flow

### Command Processing Flow

1. User invokes a slash command
2. Command handler in `commands.py` receives the interaction
3. Command handler calls the corresponding function in `command_functions.py`
4. Command function processes the request and interacts with:
   - `queue_manager` for queue operations
   - `playback_manager` for playback operations
5. Results are sent back to the user

### Playback Flow

1. `play_audio()` method is called with a track entry
2. Method checks if URL refresh is needed
3. Entry is set as currently playing
4. `start_playback()` creates an FFmpeg audio source
5. Audio source is passed to the voice client with an after-playing callback
6. When playback ends, the callback:
   - Handles any errors
   - Updates the queue state
   - Plays the next track if available

### Button Interaction Flow

1. User clicks a button on the "Now Playing" message
2. Corresponding callback in `ButtonView` is triggered
3. Callback calls the appropriate function in `view_functions.py`
4. Function performs the requested action
5. View is refreshed to reflect the new state

## Extending the Bot

### Adding New Commands

To add a new command:

1. Define the command in `commands.py`:
```python
@app_commands.command(name='new_command', description='Description of the new command')
async def new_command(self, interaction: Interaction, parameter: str):
    await process_new_command(interaction, parameter)
```

2. Implement the command function in `command_functions.py`:
```python
async def process_new_command(interaction: Interaction, parameter: str):
    # Command implementation
    await interaction.followup.send(f"Processed: {parameter}")
```

3. Register the command in `setup_commands()` if needed

### Adding New Buttons

To add a new button:

1. Add the button to the `ButtonView` class in `button_view.py`:
```python
self.new_button = Button(label="New Button", style=ButtonStyle.secondary, custom_id=f"new_button-{uuid.uuid4()}")
self.new_button.callback = self.new_button_callback
```

2. Add the callback method:
```python
async def new_button_callback(self, interaction: Interaction):
    await handle_new_button(interaction, self.entry)
```

3. Implement the button handler in `view_functions.py`:
```python
async def handle_new_button(interaction: Interaction, entry: QueueEntry):
    # Button handler implementation
    await interaction.followup.send("New button clicked!")
```

4. Update the `update_buttons()` method to include your new button

### Adding New Features

To add a new feature:

1. Identify the appropriate module for your feature
2. Implement the necessary functions or classes
3. Integrate with existing components as needed
4. Update the user interface to expose the feature
5. Add appropriate error handling and logging

### Best Practices

1. **Error Handling**: Always use try-except blocks for operations that might fail
2. **Logging**: Use the logging module to track events and errors
3. **Asynchronous Programming**: Use async/await for all Discord API interactions
4. **State Management**: Update queue state and save changes after modifications
5. **User Feedback**: Provide clear feedback for all user interactions
6. **Resource Management**: Clean up resources (like voice connections) when not needed
7. **Rate Limiting**: Be mindful of API rate limits, especially for external services
