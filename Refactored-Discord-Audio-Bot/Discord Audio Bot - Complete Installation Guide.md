# Discord Audio Bot - Complete Installation Guide

This comprehensive guide will walk you through every step needed to set up and run the Discord Audio Bot with all its features. This guide is designed for users of all experience levels, from beginners to advanced developers.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Python Installation](#python-installation)
3. [Setting Up a Virtual Environment](#setting-up-a-virtual-environment)
4. [FFmpeg Installation](#ffmpeg-installation)
5. [Discord Bot Setup](#discord-bot-setup)
6. [API Keys Setup](#api-keys-setup)
   - [Discord Developer Portal](#discord-developer-portal)
   - [Last.fm API](#lastfm-api)
   - [Genius API](#genius-api)
7. [Environment Configuration](#environment-configuration)
8. [Installing Required Libraries](#installing-required-libraries)
9. [Downloading and Setting Up the Bot](#downloading-and-setting-up-the-bot)
10. [Running the Bot](#running-the-bot)
11. [Troubleshooting](#troubleshooting)
12. [Advanced Configuration](#advanced-configuration)

## Prerequisites

Before starting, ensure you have:
- Administrator access to your computer
- A stable internet connection
- A Discord account
- Basic familiarity with command line interfaces

## Python Installation

The Discord Audio Bot requires Python 3.8 or newer.

### Windows
1. Visit the [Python downloads page](https://www.python.org/downloads/)
2. Download the latest Python installer (3.10 or newer recommended)
3. Run the installer
4. **IMPORTANT**: Check the box that says "Add Python to PATH"
5. Click "Install Now"
6. Wait for the installation to complete
7. Verify the installation by opening Command Prompt and typing:
   ```
   python --version
   ```
   You should see the Python version displayed.

### macOS
1. Install Homebrew if you don't have it:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Install Python using Homebrew:
   ```
   brew install python
   ```
3. Verify the installation:
   ```
   python3 --version
   ```

### Linux (Ubuntu/Debian)
1. Update your package list:
   ```
   sudo apt update
   ```
2. Install Python and development tools:
   ```
   sudo apt install python3 python3-pip python3-dev
   ```
3. Verify the installation:
   ```
   python3 --version
   ```

## Setting Up a Virtual Environment

Virtual environments keep your project dependencies isolated from other Python projects.

### Windows
1. Open Command Prompt
2. Navigate to where you want to create your project:
   ```
   cd C:\path\to\your\project\folder
   ```
3. Create a virtual environment:
   ```
   python -m venv discord-bot-env
   ```
4. Activate the virtual environment:
   ```
   discord-bot-env\Scripts\activate
   ```
   Your command prompt should now show `(discord-bot-env)` at the beginning of the line.

### macOS/Linux
1. Open Terminal
2. Navigate to your project folder:
   ```
   cd /path/to/your/project/folder
   ```
3. Create a virtual environment:
   ```
   python3 -m venv discord-bot-env
   ```
4. Activate the virtual environment:
   ```
   source discord-bot-env/bin/activate
   ```
   Your terminal should now show `(discord-bot-env)` at the beginning of the line.

## FFmpeg Installation

FFmpeg is required for audio processing.

### Windows
1. Download the FFmpeg build from [FFmpeg.org](https://ffmpeg.org/download.html) or [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (download the "essentials" build)
2. Extract the ZIP file to a location like `C:\ffmpeg`
3. Add FFmpeg to your PATH:
   - Right-click on "This PC" or "My Computer" and select "Properties"
   - Click on "Advanced system settings"
   - Click on "Environment Variables"
   - Under "System variables", find and select "Path", then click "Edit"
   - Click "New" and add the path to the FFmpeg bin folder (e.g., `C:\ffmpeg\bin`)
   - Click "OK" on all dialogs
4. Verify the installation by opening a new Command Prompt and typing:
   ```
   ffmpeg -version
   ```

### macOS
1. Install FFmpeg using Homebrew:
   ```
   brew install ffmpeg
   ```
2. Verify the installation:
   ```
   ffmpeg -version
   ```

### Linux (Ubuntu/Debian)
1. Install FFmpeg:
   ```
   sudo apt update
   sudo apt install ffmpeg
   ```
2. Verify the installation:
   ```
   ffmpeg -version
   ```

## Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give your bot a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the "TOKEN" section, click "Copy" to copy your bot token (keep this secure!)
5. Under "Privileged Gateway Intents", enable:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
6. Save changes
7. Go to the "OAuth2" tab, then "URL Generator"
8. Select the following scopes:
   - bot
   - applications.commands
9. Select the following bot permissions:
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Add Reactions
   - Connect
   - Speak
   - Use Voice Activity
10. Copy the generated URL at the bottom
11. Paste the URL in a web browser and select the server where you want to add the bot
12. Authorize the bot

## API Keys Setup

### Discord Developer Portal
You've already obtained your Discord bot token in the previous section.

### Last.fm API
1. Visit the [Last.fm API page](https://www.last.fm/api/account/create)
2. If you don't have a Last.fm account, create one
3. Fill out the form to create an API account:
   - Application name: Discord Audio Bot
   - Application description: A Discord bot for playing music
4. After submitting, you'll receive your API key
5. Save this key for later use

### Genius API
1. Visit the [Genius API clients page](https://genius.com/api-clients)
2. Sign in or create a Genius account
3. Click "New API Client"
4. Fill in the required information:
   - App name: Discord Audio Bot
   - App website URL: (you can use your GitHub profile or just http://localhost)
   - Redirect URI: http://localhost
5. Click "Save" to create your client
6. You'll be provided with a Client ID, Client Secret, and Client Access Token
7. Save the Client Access Token for later use

## Environment Configuration

Create a `.env` file in your project directory to store your API keys securely.

1. In your project folder, create a new file named `.env`
2. Add the following lines to the file, replacing the placeholders with your actual keys:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   LASTFM_API_KEY=your_lastfm_api_key_here
   GENIUS_ACCESS_TOKEN=your_genius_access_token_here
   ```
3. Save the file

## Installing Required Libraries

There are two ways to install the required libraries:

### Option 1: Using requirements.txt (Recommended)

The bot comes with a `requirements.txt` file that lists all necessary dependencies. If it's not included, create a file named `requirements.txt` in your project directory with the following content:

```
discord.py[voice]>=2.0.0
python-dotenv>=0.19.0
yt-dlp>=2023.3.4
aiohttp>=3.8.1
mutagen>=1.45.1
lyricsgenius>=3.0.0
```

With your virtual environment activated, install all dependencies at once:

```
pip install -r requirements.txt
```

This will install all the required libraries with their appropriate versions.

### Option 2: Manual Installation

Alternatively, you can install each library individually:

```
pip install discord.py[voice] python-dotenv yt-dlp aiohttp mutagen lyricsgenius
```

This installs:
- discord.py with voice support: For Discord bot functionality
- python-dotenv: For loading environment variables
- yt-dlp: For YouTube downloading and streaming
- aiohttp: For asynchronous HTTP requests
- mutagen: For audio file metadata handling
- lyricsgenius: For fetching song lyrics

## Downloading and Setting Up the Bot

### Option 1: Using Git
If you have Git installed:

1. Clone the repository:
   ```
   git clone https://github.com/your-username/Refactored-Discord-Audio-Bot.git
   ```
2. Navigate to the bot directory:
   ```
   cd Refactored-Discord-Audio-Bot
   ```
3. Install dependencies using the requirements.txt file:
   ```
   pip install -r requirements.txt
   ```

### Option 2: Manual Download
1. Download the ZIP file containing the bot code
2. Extract the ZIP file to your project folder
3. Navigate to the extracted folder in your command line
4. Install dependencies using the requirements.txt file:
   ```
   pip install -r requirements.txt
   ```

### Setting Up the Bot
1. Create a `cookies.txt` file in the bot directory (optional, but recommended for better YouTube access)
   - You can use browser extensions like "Get cookies.txt" for Chrome or Firefox
   - Visit YouTube, export cookies to cookies.txt format
   - Place the file in the bot directory
2. Create a `downloaded-mp3s` directory in the bot folder:
   ```
   mkdir downloaded-mp3s
   ```

## Running the Bot

With everything set up, you can now run the bot:

1. Ensure your virtual environment is activated
2. Navigate to the bot directory if you're not already there
3. Run the bot:
   ```
   python bot.py
   ```
4. You should see output indicating that the bot is running and has connected to Discord

## Troubleshooting

### Bot Won't Start
- Check that your `.env` file is in the correct location and contains the correct tokens
- Ensure your Discord token is valid and hasn't been reset
- Verify that all required libraries are installed
- Try reinstalling dependencies: `pip install -r requirements.txt --force-reinstall`

### Audio Playback Issues
- Ensure FFmpeg is properly installed and in your PATH
- Check that the bot has the necessary permissions in your Discord server
- Verify that you're in a voice channel before using audio commands

### YouTube Download Issues
- Update yt-dlp to the latest version: `pip install -U yt-dlp`
- Check if your cookies.txt file is valid and up-to-date
- Some videos may be region-restricted or not available for streaming

### API Key Issues
- Verify that your API keys are correct and have the necessary permissions
- Check if you've hit any API rate limits
- Ensure your environment variables are being loaded correctly

### Dependency Issues
- If you encounter dependency conflicts, try creating a fresh virtual environment
- Update pip before installing requirements: `pip install --upgrade pip`
- Install dependencies one by one to identify problematic packages

## Advanced Configuration

### Custom Command Prefix
You can change the command prefix in the `config.py` file.

### Audio Quality Settings
You can adjust audio quality settings in the `playback.py` file:
- Look for the `FFmpegPCMAudio` options
- Adjust the volume level in the `PCMVolumeTransformer` settings

### Queue Management
The bot stores queue information in `queues.json`. You can:
- Back up this file to preserve queues between restarts
- Edit it manually (with caution) to pre-populate queues

### Custom Logging
Adjust logging settings in each file where logging is configured:
- Change log levels (DEBUG, INFO, WARNING, ERROR)
- Modify log file names or formats

### Multiple Server Support
The bot automatically supports multiple Discord servers. Each server gets its own queue and playback state.

---

Congratulations! You've successfully set up the Discord Audio Bot with all its features. If you encounter any issues not covered in this guide, check the bot's documentation or seek help from the community.

Remember to keep your API keys and tokens secure and never share them publicly.
