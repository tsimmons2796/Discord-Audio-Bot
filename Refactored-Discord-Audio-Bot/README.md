#!/usr/bin/env python3
"""
Discord Audio Bot - README
This file provides an overview of the project structure and usage instructions.
"""

# Discord Audio Bot

This project contains a Discord Audio Bot with installation scripts and documentation.

## Project Structure

- `Discord Audio Bot Business Rules.md` - Comprehensive installation guide for Windows and macOS
- `business_rules.md` - Documentation of the bot's business logic and rules
- `setup.py` - Cross-platform Python setup script
- `setup_windows.bat` - Windows-specific automation script
- `setup_macos.sh` - macOS-specific automation script

## Quick Start

### Windows Users

1. Right-click on `setup_windows.bat` and select "Run as administrator"
2. Follow the on-screen prompts
3. After installation completes, edit the `.env` file with your Discord bot token
4. Run the bot by activating the virtual environment and running `python bot.py`

### macOS Users

1. Open Terminal
2. Navigate to the directory containing these files
3. Run: `chmod +x setup_macos.sh` (if not already executable)
4. Run: `./setup_macos.sh`
5. Follow the on-screen prompts
6. After installation completes, edit the `.env` file with your Discord bot token
7. Run the bot by activating the virtual environment and running `python bot.py`

## Manual Setup

If you prefer to set up manually or if the automation scripts encounter issues, please refer to the detailed instructions in `discord_bot_installation_guide.md`.

## Required Manual Steps

The following steps must be completed manually:

1. Creating a Discord Bot Application in the Discord Developer Portal
2. Obtaining the Discord Bot Token
3. Obtaining any optional API keys (Genius, Last.fm, Spotify, etc.)
4. Editing the `.env` file with your tokens and keys
5. Inviting the bot to your Discord server

## Support

If you encounter any issues with the installation or setup process, please refer to the troubleshooting section in the installation guide or contact the bot developer for assistance.
