#!/usr/bin/env python3
"""
Cross-platform setup script for Discord Audio Bot
This script handles the common setup tasks that work across platforms
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import urllib.request
import zipfile
import tempfile

def print_step(message):
    """Print a formatted step message"""
    print(f"\n{'='*80}\n{message}\n{'='*80}")

def run_command(command, shell=False):
    """Run a command and return its output"""
    try:
        if isinstance(command, list) and not shell:
            print(f"Running: {' '.join(command)}")
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            print(f"Running: {command}")
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Error output: {e.stderr}")
        return None

def check_python_version():
    """Check if Python version is compatible"""
    print_step("Checking Python version")
    
    major, minor = sys.version_info.major, sys.version_info.minor
    print(f"Detected Python {major}.{minor}")
    
    if major < 3 or (major == 3 and minor < 8):
        print("Error: Python 3.8 or higher is required")
        print("Please install a compatible Python version and try again")
        sys.exit(1)
    
    print("Python version check passed!")

def check_ffmpeg_installation():
    """Check if FFmpeg is installed and install it if needed"""
    print_step("Checking FFmpeg installation")
    
    # Check if ffmpeg is in PATH
    try:
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("FFmpeg is already installed:")
        print(result.stdout.splitlines()[0])
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("FFmpeg is not installed or not in PATH")
    
    # Install FFmpeg based on platform
    if platform.system() == "Darwin":  # macOS
        try:
            # Check if Homebrew is installed
            brew_check = subprocess.run(["brew", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print("Homebrew is installed, using it to install FFmpeg...")
            
            # Install FFmpeg using Homebrew
            subprocess.run(["brew", "install", "ffmpeg"], check=True)
            print("FFmpeg installed successfully via Homebrew")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Homebrew is not installed. Please install Homebrew first:")
            print("/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            print("Then run this setup script again.")
            return False
    
    elif platform.system() == "Linux":
        # Detect package manager and install
        try:
            # Try apt (Debian/Ubuntu)
            subprocess.run(["apt", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("Installing FFmpeg using apt...")
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=True)
            print("FFmpeg installed successfully via apt")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            try:
                # Try dnf (Fedora)
                subprocess.run(["dnf", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print("Installing FFmpeg using dnf...")
                subprocess.run(["sudo", "dnf", "install", "-y", "ffmpeg"], check=True)
                print("FFmpeg installed successfully via dnf")
                return True
            except (subprocess.SubprocessError, FileNotFoundError):
                try:
                    # Try pacman (Arch)
                    subprocess.run(["pacman", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print("Installing FFmpeg using pacman...")
                    subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"], check=True)
                    print("FFmpeg installed successfully via pacman")
                    return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    print("Could not automatically install FFmpeg. Please install it manually:")
                    print("For Debian/Ubuntu: sudo apt install ffmpeg")
                    print("For Fedora: sudo dnf install ffmpeg")
                    print("For Arch: sudo pacman -S ffmpeg")
                    return False
    
    elif platform.system() == "Windows":
        print("On Windows, FFmpeg will be installed by the setup_windows.bat script.")
        print("If you're running this script directly, please run setup_windows.bat instead.")
        return True
    
    else:
        print(f"Unsupported platform: {platform.system()}")
        print("Please install FFmpeg manually and ensure it's in your PATH")
        return False

def create_virtual_environment(project_dir):
    """Create and activate a virtual environment"""
    print_step("Creating virtual environment")
    
    venv_dir = os.path.join(project_dir, "venv")
    
    # Check if venv already exists
    if os.path.exists(venv_dir):
        print(f"Virtual environment already exists at {venv_dir}")
        return venv_dir
    
    # Create venv
    try:
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        print(f"Created virtual environment at {venv_dir}")
        return venv_dir
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        sys.exit(1)

def install_requirements(project_dir, venv_dir):
    """Install required packages in the virtual environment"""
    print_step("Installing required packages")
    
    requirements_file = os.path.join(project_dir, "requirements.txt")
    
    # Check if requirements.txt exists
    if not os.path.exists(requirements_file):
        print("Creating a basic requirements.txt file")
        with open(requirements_file, "w") as f:
            f.write("discord.py[voice]>=2.0.0\n"
                    "python-dotenv>=0.19.0\n"
                    "yt-dlp>=2023.3.4\n"
                    "aiohttp>=3.8.1\n"
                    "mutagen>=1.45.1\n"
                    "lyricsgenius>=3.0.0\n"
                    "PyNaCl>=1.4.0\n")
    
    # Determine pip path based on platform
    if platform.system() == "Windows":
        pip_path = os.path.join(venv_dir, "Scripts", "pip")
        python_path = os.path.join(venv_dir, "Scripts", "python")
    else:
        pip_path = os.path.join(venv_dir, "bin", "pip")
        python_path = os.path.join(venv_dir, "bin", "python")
    
    # Upgrade pip
    try:
        subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        print("Upgraded pip to the latest version")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to upgrade pip: {e}")
    
    # Install requirements
    try:
        print(f"Installing packages from {requirements_file}...")
        subprocess.run([pip_path, "install", "-r", requirements_file], check=True)
        
        # Verify all packages are installed
        print("Verifying package installation...")
        with open(requirements_file, 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        for req in requirements:
            # Extract package name (remove version specifiers)
            package_name = req.split('>=')[0].split('==')[0].split('[')[0].strip()
            try:
                # Try to import the package to verify installation
                subprocess.run([python_path, "-c", f"import {package_name.replace('-', '_')}"], check=True)
                print(f"✓ {package_name} installed successfully")
            except subprocess.CalledProcessError:
                print(f"⚠ {package_name} may not be installed correctly")
                # Try to reinstall the package
                subprocess.run([pip_path, "install", "--force-reinstall", req], check=True)
        
        print("Successfully installed all required packages")
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        sys.exit(1)

def create_env_template(project_dir):
    """Create a template .env file if it doesn't exist"""
    print_step("Creating .env template file")
    
    env_file = os.path.join(project_dir, ".env")
    
    if os.path.exists(env_file):
        print(".env file already exists, skipping creation")
        return
    
    env_content = """# Discord Bot Token (Required)
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
"""
    
    try:
        with open(env_file, "w") as f:
            f.write(env_content)
        print(f"Created .env template file at {env_file}")
        print("IMPORTANT: You must edit this file to add your Discord bot token and other API keys")
    except Exception as e:
        print(f"Error creating .env file: {e}")

def download_bot_code(project_dir):
    """Download bot code if not already present"""
    print_step("Checking for bot code")
    
    # Check if bot.py exists as a simple check for existing code
    bot_py = os.path.join(project_dir, "bot.py")
    
    if os.path.exists(bot_py):
        print("Bot code appears to be already present, skipping download")
        return
    
    print("Bot code not found. Creating placeholder files...")
    
    # Create a simple bot.py placeholder
    bot_py_content = """#!/usr/bin/env python3
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Discord token from environment variables
TOKEN = os.getenv('discord_token')
if not TOKEN:
    raise ValueError("No Discord token found. Please add your token to the .env file.")

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# Create bot instance
bot = commands.Bot(command_prefix='.', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

@bot.command(name='ping')
async def ping(ctx):
    #Check if the bot is responsive"
    await ctx.send('Pong! Bot is working.')

@bot.command(name='hello')
async def hello(ctx):
    #Say hello to the user
    await ctx.send(f'Hello, {ctx.author.mention}!')

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)
"""
    
    try:
        with open(bot_py, "w") as f:
            f.write(bot_py_content)
        print(f"Created placeholder bot.py file at {bot_py}")
        
        # Make bot.py executable on Unix-like systems
        if platform.system() != "Windows":
            os.chmod(bot_py, 0o755)
    except Exception as e:
        print(f"Error creating bot.py file: {e}")

def print_next_steps():
    """Print instructions for next steps"""
    print_step("Setup Complete - Next Steps")
    
    print("""
IMPORTANT: Before running the bot, you need to:

1. Create a Discord Bot Application:
   - Go to https://discord.com/developers/applications
   - Create a new application and add a bot
   - Enable the required intents (Presence, Server Members, Message Content)
   - Copy your bot token

2. Edit the .env file:
   - Add your Discord bot token
   - Add any optional API keys for enhanced functionality

3. Invite the bot to your server:
   - Generate an invite URL from the Discord Developer Portal
   - Open the URL in your browser and select your server

4. Run the bot:
   - Activate the virtual environment:
     - Windows: .\\venv\\Scripts\\activate
     - macOS/Linux: source venv/bin/activate
   - Run: python bot.py

For detailed instructions, refer to the installation guide.
""")

def main():
    """Main function to run the setup process"""
    print_step("Discord Audio Bot Setup")
    
    # Get the project directory (where this script is located)
    project_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Project directory: {project_dir}")
    
    # Check Python version
    check_python_version()
    
    # Check FFmpeg installation
    ffmpeg_installed = check_ffmpeg_installation()
    if not ffmpeg_installed and platform.system() != "Windows":
        print("WARNING: FFmpeg installation could not be completed automatically.")
        print("The bot requires FFmpeg to function properly.")
        print("Please install FFmpeg manually before running the bot.")
        user_input = input("Do you want to continue with the setup anyway? (y/n): ")
        if user_input.lower() != 'y':
            print("Setup aborted. Please install FFmpeg and run the setup again.")
            sys.exit(1)
    
    # Download bot code if needed
    download_bot_code(project_dir)
    
    # Create virtual environment
    venv_dir = create_virtual_environment(project_dir)
    
    # Install requirements
    install_requirements(project_dir, venv_dir)
    
    # Create .env template
    create_env_template(project_dir)
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()
