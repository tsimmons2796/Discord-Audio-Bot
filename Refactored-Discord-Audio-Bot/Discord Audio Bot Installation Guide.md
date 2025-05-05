# Discord Audio Bot Installation Guide

This guide provides detailed instructions for setting up and running the Discord Audio Bot on both Windows and macOS operating systems.

## Part 1: Windows Installation

These steps will guide you through installing the necessary prerequisites and the bot itself on a Windows machine.

### Step 1: Install Prerequisites

**1.1 Install Python:**

*   **Download:** Go to the official Python website: [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
*   Download the latest stable Python 3.x installer (e.g., Python 3.10 or 3.11). Choose the "Windows installer (64-bit)" recommended version.
*   **Run Installer:** Double-click the downloaded installer.
*   **IMPORTANT:** On the first screen of the installer, make sure to check the box that says **"Add Python X.X to PATH"** (where X.X is the version number). This is crucial for running Python from the command line.
*   Click **"Install Now"** and follow the prompts. Administrator privileges may be required.
*   **Verify Installation:** Open Command Prompt (search for `cmd` in the Start menu) and type `python --version` and press Enter. You should see the installed Python version printed.

**1.2 Install Git (Optional but Recommended):**

*   Git is recommended for easily downloading and updating the bot project.
*   **Download:** Go to the Git website: [https://git-scm.com/download/win](https://git-scm.com/download/win)
*   Download the latest 64-bit Git for Windows setup.
*   **Run Installer:** Run the downloaded installer. You can generally accept the default settings during installation.
*   **Verify Installation:** Open a new Command Prompt and type `git --version`. You should see the installed Git version.

**1.3 Install FFmpeg:**

*   FFmpeg is required for processing audio.
*   **Download:**
    *   Go to the FFmpeg Builds page: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
    *   Scroll down to the "release builds" section.
    *   Download the `ffmpeg-release-full.7z` archive.
*   **Extract:** You will need a tool like 7-Zip ([https://www.7-zip.org/](https://www.7-zip.org/)) to extract the `.7z` archive.
    *   Install 7-Zip if you don't have it.
    *   Right-click the downloaded `ffmpeg-release-full.7z` file, choose 7-Zip, and select "Extract Here" or "Extract to ffmpeg-release-full/". This will create a folder containing the FFmpeg files.
*   **Add to PATH:** This is the most important step to make FFmpeg accessible to the bot.
    *   Open the extracted FFmpeg folder, and then open the `bin` subfolder. Copy the full path to this `bin` folder (e.g., `C:\Users\YourUsername\Downloads\ffmpeg-release-full\bin`).
    *   Search for "Environment Variables" in the Windows Start menu and select "Edit the system environment variables".
    *   In the System Properties window, click the "Environment Variables..." button.
    *   In the "System variables" section (or "User variables" if you only want it for your user), find the `Path` variable, select it, and click "Edit...".
    *   Click "New" and paste the path to the FFmpeg `bin` folder you copied earlier.
    *   Click "OK" on all open windows to save the changes.
*   **Verify Installation:** Open a *new* Command Prompt window (important: existing ones won't see the updated PATH) and type `ffmpeg -version`. You should see FFmpeg version information printed.

### Step 2: Download the Bot Project

Choose *one* of the following methods:

**Method A: Using Git (Recommended)**

1.  Open Command Prompt.
2.  Navigate to the directory where you want to store the project (e.g., `cd C:\Users\YourUsername\Projects`).
3.  Clone the repository (replace `<repository_url>` with the actual URL if available, otherwise use the provided zip file method):
    ```bash
    git clone <repository_url> Refactored-Discord-Audio-Bot
    cd Refactored-Discord-Audio-Bot
    ```
    *If you only have the zip file:* Proceed to Method B.

**Method B: Using the Zip File**

1.  Locate the `Refactored-Discord-Audio-Bot.zip` file you downloaded.
2.  Create a folder where you want to keep the bot project (e.g., `C:\Users\YourUsername\Projects\DiscordBot`).
3.  Extract the contents of the zip file into the folder you just created. You should now have a folder structure like `C:\Users\YourUsername\Projects\DiscordBot\Refactored-Discord-Audio-Bot\...` containing files like `bot.py`, `requirements.txt`, etc.
4.  Open Command Prompt and navigate into the extracted project folder:
    ```bash
    cd C:\Users\YourUsername\Projects\DiscordBot\Refactored-Discord-Audio-Bot
    ```

### Step 3: Set Up Virtual Environment and Install Dependencies

Using a virtual environment keeps the bot's dependencies separate from your global Python installation.

1.  **Create Virtual Environment:** In the Command Prompt, while inside the `Refactored-Discord-Audio-Bot` project directory, run:
    ```bash
    python -m venv venv
    ```
    This creates a `venv` folder within your project directory.

2.  **Activate Virtual Environment:** Run:
    ```bash
    .\venv\Scripts\activate
    ```
    Your command prompt line should now start with `(venv)`.

3.  **Upgrade Pip:** Ensure you have the latest version of pip:
    ```bash
    python -m pip install --upgrade pip
    ```

4.  **Install Dependencies:** Install all required Python packages from the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
    This command will download and install `discord.py[voice]`, `yt-dlp`, `python-dotenv`, and all other necessary libraries.

*You have now completed the installation steps specific to Windows. Proceed to Part 3: Configuration and Setup.*



## Part 2: macOS Installation

These steps will guide you through installing the necessary prerequisites and the bot itself on a macOS machine.

### Step 1: Install Prerequisites

**1.1 Install Homebrew (Package Manager):**

*   Homebrew simplifies installing software on macOS. If you don't have it, open the Terminal application (Applications > Utilities > Terminal).
*   Paste the following command into the Terminal and press Enter. Follow the on-screen instructions:
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```
*   After installation, follow any instructions given by the Homebrew installer to add Homebrew to your PATH (this usually involves running a couple of commands shown at the end of the installation process).
*   **Verify Installation:** Close and reopen the Terminal, then type `brew --version` and press Enter. You should see the Homebrew version.

**1.2 Install Python 3:**

*   macOS comes with an older version of Python, but you need Python 3. Use Homebrew to install it:
    ```bash
    brew install python3
    ```
*   **Verify Installation:** In the Terminal, type `python3 --version`. You should see the installed Python 3 version.

**1.3 Install Git (Usually Pre-installed):**

*   Git is often pre-installed with Xcode Command Line Tools. Check if it's installed:
    ```bash
    git --version
    ```
*   If Git is not installed, or you want the latest version, install it with Homebrew:
    ```bash
    brew install git
    ```

**1.4 Install FFmpeg:**

*   Use Homebrew to install FFmpeg:
    ```bash
    brew install ffmpeg
    ```
*   **Verify Installation:** In the Terminal, type `ffmpeg -version`. You should see FFmpeg version information.

### Step 2: Download the Bot Project

Choose *one* of the following methods:

**Method A: Using Git (Recommended)**

1.  Open Terminal.
2.  Navigate to the directory where you want to store the project (e.g., `cd ~/Projects`).
3.  Clone the repository (replace `<repository_url>` with the actual URL if available, otherwise use the provided zip file method):
    ```bash
    git clone <repository_url> Refactored-Discord-Audio-Bot
    cd Refactored-Discord-Audio-Bot
    ```
    *If you only have the zip file:* Proceed to Method B.

**Method B: Using the Zip File**

1.  Locate the `Refactored-Discord-Audio-Bot.zip` file you downloaded (likely in your `~/Downloads` folder).
2.  Create a folder where you want to keep the bot project (e.g., `mkdir -p ~/Projects/DiscordBot`).
3.  Extract the contents of the zip file into the folder you just created. You can often double-click the zip file in Finder, or use the Terminal:
    ```bash
    unzip ~/Downloads/Refactored-Discord-Audio-Bot.zip -d ~/Projects/DiscordBot/
    ```
    This should create a folder structure like `~/Projects/DiscordBot/Refactored-Discord-Audio-Bot/...`.
4.  Open Terminal and navigate into the extracted project folder:
    ```bash
    cd ~/Projects/DiscordBot/Refactored-Discord-Audio-Bot
    ```

### Step 3: Set Up Virtual Environment and Install Dependencies

Using a virtual environment keeps the bot's dependencies separate.

1.  **Create Virtual Environment:** In the Terminal, while inside the `Refactored-Discord-Audio-Bot` project directory, run:
    ```bash
    python3 -m venv venv
    ```
    This creates a `venv` folder within your project directory.

2.  **Activate Virtual Environment:** Run:
    ```bash
    source venv/bin/activate
    ```
    Your Terminal prompt should now start with `(venv)`.

3.  **Upgrade Pip:** Ensure you have the latest version of pip:
    ```bash
    python3 -m pip install --upgrade pip
    ```

4.  **Install Dependencies:** Install all required Python packages from the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
    This command will download and install `discord.py[voice]`, `yt-dlp`, `python-dotenv`, and all other necessary libraries.

*You have now completed the installation steps specific to macOS. Proceed to Part 3: Configuration and Setup.*



## Part 3: Configuration and Setup

After installing the prerequisites and the bot's dependencies on either Windows or macOS, you need to configure the bot with necessary API tokens and settings.

### Step 1: Create a Discord Bot Application

1.  **Go to Discord Developer Portal:** Open your web browser and navigate to [https://discord.com/developers/applications](https://discord.com/developers/applications).
2.  **Login:** Log in with your Discord account.
3.  **New Application:** Click the "New Application" button in the top-right corner.
4.  **Name:** Give your application a name (e.g., "My Audio Bot") and click "Create".
5.  **Navigate to Bot Settings:** In the left-hand menu, click on "Bot".
6.  **Add Bot:** Click the "Add Bot" button and confirm by clicking "Yes, do it!".
7.  **Get Token:** Under the bot's username, you'll see a section labeled "TOKEN". Click the "Reset Token" button (or "Copy" if you've generated one before and saved it). **Treat this token like a password - do not share it!** Copy the token immediately and store it securely for the next step.
8.  **Enable Privileged Intents:** Scroll down to the "Privileged Gateway Intents" section.
    *   Enable **"Presence Intent"**. 
    *   Enable **"Server Members Intent"**. 
    *   Enable **"Message Content Intent"**.
    *   *Note:* Discord requires verification for bots in over 100 servers using these intents, but it's necessary for many bot features to work correctly in smaller servers.
9.  **Save Changes:** Click the "Save Changes" button at the bottom if it appears.

### Step 2: Obtain Other API Keys (Optional but Recommended)

The bot's `config.py` file indicates it can use API keys for enhanced features like lyrics fetching or music discovery. Obtaining these is optional if you don't need those specific features, but recommended for full functionality.

*   **Genius API Token (for Lyrics):**
    *   Go to [https://genius.com/api-clients](https://genius.com/api-clients).
    *   Create a new API client.
    *   Generate your client access token.
*   **MusicBrainz User Agent (for Metadata):**
    *   You typically just need to define a descriptive user agent string. Format: `YourAppName/Version ( ContactInfo )`. Example: `MyDiscordBot/1.0 ( myemail@example.com )`.
*   **Last.fm API Key (for Discovery/Metadata):**
    *   Go to [https://www.last.fm/api/account/create](https://www.last.fm/api/account/create).
    *   Create an API account and get your API key.
*   **Spotify Client ID & Secret (for Discovery/Metadata):**
    *   Go to the Spotify Developer Dashboard: [https://developer.spotify.com/dashboard/](https://developer.spotify.com/dashboard/)
    *   Create an app and get your Client ID and Client Secret.

### Step 3: Create the `.env` Configuration File

This file stores your secret tokens securely.

1.  **Navigate to Project Directory:** Open Command Prompt (Windows) or Terminal (macOS) and make sure you are in the `Refactored-Discord-Audio-Bot` directory where `bot.py` is located.
2.  **Create `.env` file:** Create a new file named exactly `.env` (note the leading dot and no extension) in this directory. You can do this using a text editor or via the command line:
    *   *Windows (Command Prompt):* `copy con .env` then press Enter, type the content (see below), press Ctrl+Z, and then Enter.
    *   *macOS (Terminal):* `touch .env` then open the file in a text editor (`nano .env` or `open -t .env`).
3.  **Add Tokens:** Open the `.env` file with a text editor (like Notepad, VS Code, Nano, etc.) and add the following lines, replacing the placeholder values with your actual tokens and keys:

    ```dotenv
    # Discord Bot Token (Required)
discord_token=YOUR_DISCORD_BOT_TOKEN_HERE

    # Genius API Token (Optional - for lyrics)
genius_api_token=YOUR_GENIUS_API_TOKEN_HERE

    # MusicBrainz User Agent (Optional - for metadata)
    # Replace with your app name/version and contact info
    MUSICBRAINZ_USER_AGENT=MyDiscordBot/1.0 ( username@example.com )

    # Last.fm API Key (Optional - for discovery/metadata)
    LASTFM_API_KEY=YOUR_LASTFM_API_KEY_HERE

    # Spotify Credentials (Optional - for discovery/metadata)
    SPOTIFY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID_HERE
    SPOTIFY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET_HERE
    ```

4.  **Save the file.** Ensure it is saved as `.env` and not `.env.txt`.

### Step 4: Invite the Bot to Your Server

1.  **Go back to Discord Developer Portal:** Navigate to your application's page.
2.  **OAuth2 Settings:** Click on "OAuth2" in the left menu, then select "URL Generator".
3.  **Scopes:** In the "Scopes" section, check the box for `bot` and `applications.commands`.
4.  **Bot Permissions:** In the "Bot Permissions" section that appears below, select the necessary permissions for an audio bot. Recommended permissions include:
    *   `View Channels`
    *   `Send Messages`
    *   `Embed Links`
    *   `Attach Files`
    *   `Read Message History`
    *   `Connect`
    *   `Speak`
    *   `Use Voice Activity`
    *   `Priority Speaker` (Optional)
5.  **Generate URL:** Scroll down to the "Generated URL" section and click "Copy".
6.  **Invite:** Paste the copied URL into your web browser's address bar and press Enter.
7.  **Select Server:** Choose the Discord server you want to add the bot to from the dropdown menu and click "Continue".
8.  **Authorize:** Review the requested permissions and click "Authorize". Complete any CAPTCHA verification if prompted.
9.  The bot should now appear in your selected Discord server's member list (it will be offline until you run the script).

*Configuration is complete. Proceed to Part 4: Running the Bot.*



## Part 4: Running the Bot

Once the bot is installed and configured, follow these steps to run it.

1.  **Open Terminal/Command Prompt:**
    *   **Windows:** Open Command Prompt (`cmd`).
    *   **macOS:** Open Terminal.

2.  **Navigate to Project Directory:** Change directory to where you extracted/cloned the bot project.
    *   **Windows Example:** `cd C:\Users\YourUsername\Projects\DiscordBot\Refactored-Discord-Audio-Bot`
    *   **macOS Example:** `cd ~/Projects/DiscordBot/Refactored-Discord-Audio-Bot`

3.  **Activate Virtual Environment:**
    *   **Windows:** `.\venv\Scripts\activate`
    *   **macOS:** `source venv/bin/activate`
    *   Your prompt should now start with `(venv)`.

4.  **Run the Bot Script:**
    *   **Windows:** `python bot.py`
    *   **macOS:** `python3 bot.py`

5.  **Bot Online:** You should see output in the terminal indicating the bot is connecting and ready (e.g., `YourBotName#1234 is now connected and ready.`). The bot should now appear as online in your Discord server.

6.  **Keep Terminal Open:** The terminal window where you ran the bot **must remain open** for the bot to stay online. Closing the window will shut down the bot.

7.  **Stopping the Bot:** To stop the bot, go to the terminal window where it's running and press `Ctrl + C`.

*The bot is now running and ready to accept commands in your Discord server!*



## Part 5: Basic Usage and Further Documentation

Now that your bot is installed and running, you can interact with it in your Discord server.

### Basic Interaction

This bot utilizes both standard Discord slash commands and custom dot commands:

*   **Slash Commands:** Type `/` in the chat bar within your Discord server. Discord should automatically show a list of available commands registered by the bot (e.g., `/play`, `/skip`, `/list_queue`, `/help`, etc.). Select a command and provide any required arguments (like a YouTube URL or song title for `/play`).
*   **Dot Commands:** The bot also responds to specific commands starting with a dot (`.`). Based on the code, these include commands like `.mp3_list` and `.mp3_list_next`. Type these directly into the chat.

### Finding Commands

*   Use the `/help` slash command within Discord to get a list of available commands directly from the bot.

### Detailed Documentation

The project folder contains several documentation files that provide more in-depth information about the bot's features, commands, and logic:

*   `Discord Audio Bot - Comprehensive Command Documentation.md`: Detailed descriptions of each command.
*   `user_guide.md`: A guide focused on using the bot's features.
*   `business_rules.md`: Explains the underlying logic and rules the bot follows.
*   `Discord Audio Bot - Command Logic and Flow.md`: Information on how commands are processed.
*   `DOCUMENTATION.md`: General documentation overview.

Refer to these files within the `Refactored-Discord-Audio-Bot` project folder for comprehensive details on all functionalities.

---
*End of Installation Guide*
