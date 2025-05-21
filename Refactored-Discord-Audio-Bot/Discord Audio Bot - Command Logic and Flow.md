# Discord Audio Bot - Command Logic and Flow

This document provides a comprehensive explanation of the Discord Audio Bot's command functionality, business logic, and flow from start to finish for each command.

## Table of Contents
1. [Core Architecture](#core-architecture)
2. [Command Flow Overview](#command-flow-overview)
3. [Playback Commands](#playback-commands)
4. [Queue Management Commands](#queue-management-commands)
5. [MP3 Management Commands](#mp3-management-commands)
6. [Additional Features](#additional-features)
7. [Error Handling](#error-handling)
8. [Command Interactions](#command-interactions)

## Core Architecture

The Discord Audio Bot is built with a modular architecture consisting of these key components:

1. **Bot (bot.py)**: The main entry point that initializes the Discord client and registers commands.
2. **Commands (commands.py)**: Defines all slash commands and their parameters.
3. **Command Functions (command_functions.py)**: Contains the business logic for each command.
4. **Queue Manager (queue_manager.py)**: Manages the audio queue for each server.
5. **Playback Manager (playback.py)**: Handles audio playback and streaming.
6. **Utilities (utils.py)**: Provides helper functions for file operations, metadata extraction, etc.
7. **Button View (button_view.py)**: Manages interactive buttons for the now playing interface.

## Command Flow Overview

All commands follow this general flow:

1. User invokes a slash command in Discord
2. The command handler in `commands.py` receives the interaction
3. The handler defers the response to allow for processing time
4. The handler calls the appropriate function in `command_functions.py`
5. The command function performs the business logic
6. The function interacts with the queue manager and/or playback manager as needed
7. The function sends a response to the user
8. If audio playback is involved, the now playing interface is updated

## Playback Commands

### `/play` Command

**Purpose**: Play a YouTube video, search for a title, or play an MP3 file.

**Flow**:
1. User invokes `/play` with one of these parameters:
   - `youtube_url`: Direct YouTube URL
   - `youtube_title`: Title to search for on YouTube
   - `mp3_file`: Uploaded MP3 file
2. Command is received by `play()` in `commands.py`
3. Response is deferred to allow for processing
4. `process_play()` in `command_functions.py` is called
5. The function checks if the bot is in a voice channel, connecting if needed
6. Based on the parameter provided:
   - For MP3 files: Downloads the file, extracts metadata, creates a queue entry
   - For YouTube titles: Searches YouTube, extracts video info, creates a queue entry
   - For YouTube URLs: Checks if it's a playlist or single video and processes accordingly
7. Adds the entry to the queue
8. If nothing is currently playing, starts playback
9. Sends a confirmation message to the user

**Example**:
```
User: /play youtube_title: Never Gonna Give You Up
Bot: [defers response]
Bot: [searches YouTube]
Bot: [adds to queue]
Bot: Added 'Rick Astley - Never Gonna Give You Up' to the queue.
Bot: [starts playback if nothing is playing]
Bot: [displays now playing interface with progress bar]
```

### `/play_next_in_queue` Command

**Purpose**: Add a track to play immediately after the current one.

**Flow**:
1. User invokes `/play_next_in_queue` with parameters similar to `/play`
2. Command is received and response is deferred
3. `process_play_next()` in `command_functions.py` is called
4. The function processes the input similar to `/play`
5. Instead of adding to the end of the queue, it inserts at position 2 (after the currently playing track)
6. Sends a confirmation message to the user

### `/skip` Command

**Purpose**: Skip the currently playing track.

**Flow**:
1. User invokes `/skip`
2. Command is received and response is deferred
3. `process_skip()` in `command_functions.py` is called
4. The function checks if something is playing
5. If yes, it stops the current playback
6. The `after_playing_callback` is triggered, which automatically plays the next track
7. Sends a confirmation message to the user

### `/pause`, `/resume`, `/stop`, `/restart` Commands

These commands follow a similar pattern:
1. User invokes the command
2. Command is received and response is deferred
3. The corresponding process function is called
4. The function performs the action on the voice client
5. Updates the queue manager state as needed
6. Sends a confirmation message to the user

## Queue Management Commands

### `/list_queue` Command

**Purpose**: Display all tracks in the queue.

**Flow**:
1. User invokes `/list_queue`
2. Command is received and response is deferred
3. `process_list_queue()` in `command_functions.py` is called
4. The function gets the queue for the server
5. Creates an embed with all tracks, their durations, and other metadata
6. Sends the embed to the user

### `/shuffle` Command

**Purpose**: Randomly shuffle the queue.

**Flow**:
1. User invokes `/shuffle`
2. Command is received and response is deferred
3. `process_shuffle()` in `command_functions.py` is called
4. The function gets the queue for the server
5. Shuffles the queue using Python's `random.shuffle()`
6. Updates the queue manager
7. Sends the updated queue to the user

### `/clear_queue`, `/remove_queue`, `/remove_by_title`, `/move_to_next` Commands

These queue management commands follow a similar pattern:
1. User invokes the command with any required parameters
2. Command is received and response is deferred
3. The corresponding process function is called
4. The function modifies the queue as needed
5. Updates the queue manager
6. Sends a confirmation message to the user

## MP3 Management Commands

### `/mp3` Command

**Purpose**: Manage MP3 files (list, delete, or play).

**Flow**:
1. User invokes `/mp3` with parameters:
   - `action`: "list", "delete", or "play"
   - `filename`: (for delete/play) The filename to act on
2. Command is received and response is deferred
3. `process_mp3_management()` in `command_functions.py` is called
4. Based on the action:
   - "list": Lists all MP3 files in the downloaded-mp3s directory
   - "delete": Deletes the specified file
   - "play": Creates a queue entry for the file and plays it
5. Sends a confirmation message to the user

## Additional Features

### `/lyrics` Command

**Purpose**: Display lyrics for the current song or a specified query.

**Flow**:
1. User invokes `/lyrics` with optional `query` parameter
2. Command is received and response is deferred
3. `process_lyrics_command()` in `command_functions.py` is called
4. If no query is provided, uses the currently playing song
5. Searches for lyrics using the Genius API
6. Formats and sends the lyrics to the user

### `/volume` Command

**Purpose**: Adjust the playback volume.

**Flow**:
1. User invokes `/volume` with `volume` parameter (0-100)
2. Command is received and response is deferred
3. `process_volume_command()` in `command_functions.py` is called
4. Validates the volume range
5. Sets the volume on the voice client's audio source
6. Sends a confirmation message to the user

### `/discover` Command

**Purpose**: Discover and queue similar songs based on the current track.

**Flow**:
1. User invokes `/discover` with optional `artist_or_song` parameter
2. Command is received and response is deferred
3. `discover_and_queue_recommendations()` in `command_functions.py` is called
4. If no parameter is provided, uses the currently playing song
5. Searches for similar artists using the Last.fm API
6. Gets top tracks for those artists
7. Searches YouTube for those tracks
8. Adds them to the queue
9. Sends a confirmation message with the number of tracks queued

## Error Handling

The bot implements comprehensive error handling throughout the command flow:

1. **Input Validation**: Commands validate user input before processing
2. **API Error Handling**: Errors from external APIs (YouTube, Genius, Last.fm) are caught and reported
3. **Playback Error Recovery**: If a track fails to play, the bot attempts to play the next track
4. **File Operation Safety**: File operations include error handling to prevent crashes
5. **Asynchronous Error Handling**: All async functions include try/except blocks to catch errors

## Command Interactions

Commands interact with each other through the shared queue and playback managers:

1. **Queue State**: Commands like `/play`, `/skip`, and `/shuffle` modify the queue state
2. **Playback State**: Commands like `/pause`, `/resume`, and `/stop` modify the playback state
3. **Now Playing Interface**: Multiple commands update the now playing interface
4. **File Management**: MP3 management commands interact with the file system

This architecture allows for a cohesive user experience where commands work together seamlessly while maintaining separation of concerns in the codebase.
