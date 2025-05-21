#!/bin/bash

# Discord Audio Bot Setup for macOS
# This script automates the installation of prerequisites and setup for the Discord Audio Bot

# Print a formatted header
print_header() {
    echo "========================================================================"
    echo "$1"
    echo "========================================================================"
    echo
}

# Print a step message
print_step() {
    echo
    echo ">> $1"
    echo "---------------------------------------"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_header "Discord Audio Bot Setup for macOS"
echo "Working directory: $SCRIPT_DIR"

# Check for Homebrew and install if not present
print_step "Checking for Homebrew installation"
if ! command_exists brew; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH if needed
    if [[ $(uname -m) == "arm64" ]]; then
        echo "Adding Homebrew to PATH for Apple Silicon Mac..."
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo "Adding Homebrew to PATH for Intel Mac..."
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo "Homebrew is already installed."
    brew --version
fi

# Check for Python 3 and install if not present
print_step "Checking for Python 3 installation"
if ! command_exists python3; then
    echo "Python 3 not found. Installing Python 3..."
    brew install python3
else
    echo "Python 3 is already installed."
    python3 --version
fi

# Check for Git and install if not present
print_step "Checking for Git installation"
if ! command_exists git; then
    echo "Git not found. Installing Git..."
    brew install git
else
    echo "Git is already installed."
    git --version
fi

# Check for FFmpeg and install if not present
print_step "Checking for FFmpeg installation"
if ! command_exists ffmpeg; then
    echo "FFmpeg not found. Installing FFmpeg..."
    brew install ffmpeg
    
    # Verify installation
    if command_exists ffmpeg; then
        echo "FFmpeg installed successfully."
        ffmpeg -version | head -n 1
    else
        echo "ERROR: FFmpeg installation failed. Please install manually with 'brew install ffmpeg'."
        exit 1
    fi
else
    echo "FFmpeg is already installed."
    ffmpeg -version | head -n 1
fi

# Run the Python setup script
print_step "Running Python setup script"
python3 "$SCRIPT_DIR/setup.py"

# Verify all dependencies are installed
print_step "Verifying all dependencies"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Check if PyNaCl is installed
if python3 -c "import nacl" 2>/dev/null; then
    echo "✅ PyNaCl is installed correctly."
else
    echo "⚠️ PyNaCl is not installed. Installing now..."
    pip install PyNaCl
fi

# Check if discord.py is installed
if python3 -c "import discord" 2>/dev/null; then
    echo "✅ discord.py is installed correctly."
else
    echo "⚠️ discord.py is not installed. Installing now..."
    pip install "discord.py[voice]>=2.0.0"
fi

# Check if yt-dlp is installed
if python3 -c "import yt_dlp" 2>/dev/null; then
    echo "✅ yt-dlp is installed correctly."
else
    echo "⚠️ yt-dlp is not installed. Installing now..."
    pip install "yt-dlp>=2023.3.4"
fi

# Check if all other dependencies are installed
for package in "dotenv:python-dotenv" "aiohttp:aiohttp" "mutagen:mutagen" "lyricsgenius:lyricsgenius"; do
    module="${package%%:*}"
    pip_package="${package#*:}"
    
    if python3 -c "import $module" 2>/dev/null; then
        echo "✅ $pip_package is installed correctly."
    else
        echo "⚠️ $pip_package is not installed. Installing now..."
        pip install "$pip_package"
    fi
done

print_header "Setup complete!"
echo "To run the bot:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the bot: python bot.py"
echo
echo "Remember to edit the .env file with your Discord bot token and other API keys."
echo

exit 0
