# Discord Audio Bot - Comprehensive Command Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Core Architecture](#core-architecture)
3. [Command Flow Patterns](#command-flow-patterns)
4. [Playback Commands](#playback-commands)
5. [Queue Management Commands](#queue-management-commands)
6. [MP3 Management Commands](#mp3-management-commands)
7. [Additional Features](#additional-features)
8. [Command Interactions](#command-interactions)
9. [Error Handling](#error-handling)

## Introduction

This document provides a comprehensive explanation of the Discord Audio Bot's command functionality, business logic, and flow from start to finish for each command. It details how commands interact with each other and the underlying systems, with examples of typical command flows.

## Core Architecture

The Discord Audio Bot is built with a modular architecture consisting of these key components:

1. **Bot (bot.py)**: The main entry point that initializes the Discord client and registers commands.
2. **Commands (commands.py)**: Defines all slash commands and their parameters.
3. **Command Functions (command_functions.py)**: Contains the business logic for each command.
4. **Queue Manager (queue_manager.py)**: Manages the audio queue for each server.
5. **Playback Manager (playback.py)**: Handles audio playback and streaming.
6. **Utilities (utils.py)**: Provides helper functions for file operations, metadata extraction, etc.
7. **Button View (button_view.py)**: Manages interactive buttons for the now playing interface.

### Component Interactions

The components interact in the following way:

```
User Input → Commands → Command Functions → Queue Manager/Playback Manager → Discord API
```

- **Commands** receive user input and delegate to **Command Functions**
- **Command Functions** implement business logic and interact with **Queue Manager** and **Playback Manager**
- **Queue Manager** maintains the state of audio queues for each server
- **Playback Manager** handles the actual audio playback through Discord's voice system
- **Utilities** provide helper functions used by multiple components

## Command Flow Patterns

All commands follow one of these general flow patterns:

### Standard Command Flow

1. User invokes a slash command in Discord
2. The command handler in `commands.py` receives the interaction
3. The handler defers the response to allow for processing time
4. The handler calls the appropriate function in `command_functions.py`
5. The command function performs the business logic
6. The function interacts with the queue manager and/or playback manager as needed
7. The function sends a response to the user

### Playback Command Flow

1. User invokes a playback-related slash command
2. The command handler receives and defers the interaction
3. The handler calls the appropriate function in `command_functions.py`
4. The function interacts with the playback manager
5. The playback manager updates the currently playing track
6. The now playing interface is updated
7. The function sends a response to the user

### Queue Management Command Flow

1. User invokes a queue-related slash command
2. The command handler receives and defers the interaction
3. The handler calls the appropriate function in `command_functions.py`
4. The function interacts with the queue manager
5. The queue manager updates the queue state
6. The function sends a response to the user with the updated queue information

## Playback Commands

### `/play` Command

**Purpose**: Play a YouTube video, search for a title, or play an MP3 file.

**Parameters**:
- `youtube_url` (optional): Direct YouTube URL
- `youtube_title` (optional): Title to search for on YouTube
- `mp3_file` (optional): Uploaded MP3 file

**Business Logic**:
1. Check if the bot is in a voice channel, connecting if needed
2. Based on the parameter provided:
   - For MP3 files: Downloads the file, extracts metadata, creates a queue entry
   - For YouTube titles: Searches YouTube, extracts video info, creates a queue entry
   - For YouTube URLs: Checks if it's a playlist or single video and processes accordingly
3. Adds the entry to the queue
4. If nothing is currently playing, starts playback

**Example Flow**:
```
User: /play youtube_title: Never Gonna Give You Up
Bot: [defers response]
Bot: [searches YouTube]
Bot: [adds to queue]
Bot: Added 'Rick Astley - Never Gonna Give You Up' to the queue.
Bot: [starts playback if nothing is playing]
Bot: [displays now playing interface with progress bar]
```

**Implementation Details**:
- The command is defined in `commands.py` in the `play()` method
- The business logic is implemented in `command_functions.py` in the `process_play()` function
- For YouTube URLs, it uses `yt_dlp` to extract video information
- For MP3 files, it uses `download_file()` and `extract_mp3_metadata()` from `utils.py`
- Playback is handled by `playback_manager.play_audio()`

### `/play_next_in_queue` Command

**Purpose**: Add a track to play immediately after the current one.

**Parameters**:
- Same as `/play` command

**Business Logic**:
1. Process the input similar to `/play`
2. Instead of adding to the end of the queue, insert at position 1 (after the currently playing track)
3. If nothing is playing, start playback

**Example Flow**:
```
User: /play_next_in_queue youtube_url: https://www.youtube.com/watch?v=dQw4w9WgXcQ
Bot: [defers response]
Bot: [processes URL]
Bot: [inserts at position 1 in queue]
Bot: 'Rick Astley - Never Gonna Give You Up' added to the queue at position 2.
```

**Implementation Details**:
- The command is defined in `commands.py` in the `play_next()` method
- The business logic is implemented in `command_functions.py` in the `process_play_next()` function
- Uses the same underlying mechanisms as `/play` but inserts at a different position

### `/skip` Command

**Purpose**: Skip the currently playing track.

**Business Logic**:
1. Check if something is playing
2. If yes, stop the current playback
3. The `after_playing_callback` is triggered, which automatically plays the next track

**Example Flow**:
```
User: /skip
Bot: [defers response]
Bot: [stops current playback]
Bot: Skipped 'Current Song Title'
Bot: [automatically starts playing next song]
Bot: [displays new now playing interface]
```

**Implementation Details**:
- The command is defined in `commands.py` in the `skip()` method
- The business logic is implemented in `command_functions.py` in the `process_skip()` function
- Uses `voice_client.stop()` to stop playback
- The `after_playing_callback` in `playback.py` handles playing the next track

### `/pause` Command

**Purpose**: Pause the currently playing track.

**Business Logic**:
1. Check if something is playing
2. If yes, pause the playback
3. Update the queue manager state

**Example Flow**:
```
User: /pause
Bot: [defers response]
Bot: [pauses playback]
Bot: Paused 'Current Song Title'
```

**Implementation Details**:
- The command is defined in `commands.py` in the `pause()` method
- The business logic is implemented in `command_functions.py` in the `process_pause()` function
- Uses `voice_client.pause()` to pause playback
- Updates `queue_manager.is_paused = True`
- Records the pause start time for accurate progress tracking

### `/resume` Command

**Purpose**: Resume playback if it is paused.

**Business Logic**:
1. Check if playback is paused
2. If yes, resume playback
3. Update the queue manager state

**Example Flow**:
```
User: /resume
Bot: [defers response]
Bot: [resumes playback]
Bot: Resumed 'Current Song Title'
```

**Implementation Details**:
- The command is defined in `commands.py` in the `resume()` method
- The business logic is implemented in `command_functions.py` in the `process_resume()` function
- Uses `voice_client.resume()` to resume playback
- Updates `queue_manager.is_paused = False`
- Calculates and updates the total paused duration for accurate progress tracking

### `/stop` Command

**Purpose**: Stop playback and disconnect the bot from the voice channel.

**Business Logic**:
1. Check if the bot is in a voice channel
2. If yes, stop playback and disconnect
3. Update the queue manager state

**Example Flow**:
```
User: /stop
Bot: [defers response]
Bot: [stops playback]
Bot: [disconnects from voice channel]
Bot: Playback stopped and disconnected from voice channel.
```

**Implementation Details**:
- The command is defined in `commands.py` in the `stop()` method
- The business logic is implemented in `command_functions.py` in the `process_stop()` function
- Sets `queue_manager.stop_is_triggered = True` to prevent automatic next track playback
- Uses `voice_client.stop()` to stop playback
- Uses `voice_client.disconnect()` to disconnect from the voice channel

### `/restart` Command

**Purpose**: Restart the currently playing track from the beginning.

**Business Logic**:
1. Check if something is playing
2. If yes, stop the current playback
3. Set the restart flag to prevent queue advancement
4. Play the same track again from the beginning

**Example Flow**:
```
User: /restart
Bot: [defers response]
Bot: [stops current playback]
Bot: [sets restart flag]
Bot: [starts playing the same track from beginning]
Bot: Restarted 'Current Song Title'
```

**Implementation Details**:
- The command is defined in `commands.py` in the `restart()` method
- The business logic is implemented in `command_functions.py` in the `process_restart()` function
- Sets `queue_manager.is_restarting = True` to prevent queue advancement
- Uses `voice_client.stop()` to stop playback
- Calls `playback_manager.play_audio()` with the same entry to restart

## Queue Management Commands

### `/list_queue` Command

**Purpose**: Display all tracks in the queue.

**Business Logic**:
1. Get the queue for the server
2. Create an embed with all tracks, their durations, and other metadata
3. Send the embed to the user

**Example Flow**:
```
User: /list_queue
Bot: [defers response]
Bot: [retrieves queue]
Bot: [creates embed with queue information]
Bot: [sends embed with queue listing]
```

**Implementation Details**:
- The command is defined in `commands.py` in the `list_queue()` method
- The business logic is implemented in `command_functions.py` in the `process_list_queue()` function
- Uses Discord embeds to format the queue information
- Handles pagination if the queue is too long for a single message

### `/shuffle` Command

**Purpose**: Randomly shuffle the queue.

**Business Logic**:
1. Get the queue for the server
2. Shuffle the queue using Python's `random.shuffle()`
3. Update the queue manager
4. Send the updated queue to the user

**Example Flow**:
```
User: /shuffle
Bot: [defers response]
Bot: [retrieves queue]
Bot: [shuffles queue]
Bot: [updates queue manager]
Bot: Queue has been shuffled.
Bot: [sends updated queue listing]
```

**Implementation Details**:
- The command is defined in `commands.py` in the `shuffle()` method
- The business logic is implemented in `command_functions.py` in the `process_shuffle()` function
- Sets `queue_manager.has_been_shuffled = True` to track that the queue has been shuffled
- Resets arrangement flags on all entries

### `/remove_by_title` Command

**Purpose**: Remove a track from the queue by title.

**Parameters**:
- `title`: The title of the track to remove

**Business Logic**:
1. Get the queue for the server
2. Find and remove all entries with the matching title
3. Update the queue manager
4. Clean up any associated MP3 files if needed

**Example Flow**:
```
User: /remove_by_title title: Never Gonna Give You Up
Bot: [defers response]
Bot: [retrieves queue]
Bot: [removes matching entries]
Bot: [updates queue manager]
Bot: Removed 'Never Gonna Give You Up' from the queue.
```

**Implementation Details**:
- The command is defined in `commands.py` in the `remove_by_title()` method
- The business logic is implemented in `command_functions.py` in the `process_remove_by_title()` function
- Uses list comprehension to filter out matching entries
- Calls `delete_file()` from `utils.py` for any MP3 files that need cleanup

### `/remove_queue` Command

**Purpose**: Remove a track from the queue by index.

**Parameters**:
- `index`: The index of the track to remove

**Business Logic**:
1. Get the queue for the server
2. Remove the entry at the specified index
3. Update the queue manager
4. Clean up any associated MP3 files if needed

**Example Flow**:
```
User: /remove_queue index: 3
Bot: [defers response]
Bot: [retrieves queue]
Bot: [removes entry at index 3]
Bot: [updates queue manager]
Bot: Removed 'Song Title' from the queue.
```

**Implementation Details**:
- The command is defined in `commands.py` in the `remove_queue()` method
- The business logic is implemented in `command_functions.py` in the `process_remove_queue()` function
- Adjusts the index to account for 0-based indexing
- Calls `delete_file()` from `utils.py` for any MP3 files that need cleanup

### `/clear_queue` Command

**Purpose**: Clear the queue except the currently playing entry.

**Business Logic**:
1. Get the queue for the server
2. Keep only the currently playing entry (if any)
3. Update the queue manager
4. Clean up any associated MP3 files if needed

**Example Flow**:
```
User: /clear_queue
Bot: [defers response]
Bot: [retrieves queue]
Bot: [clears queue except current entry]
Bot: [updates queue manager]
Bot: The queue for server 'Server Name' has been cleared, except the currently playing entry.
```

**Implementation Details**:
- The command is defined in `commands.py` in the `clear_queue()` method
- The business logic is implemented in `command_functions.py` in the `process_clear_queue()` function
- Preserves the currently playing entry if it exists
- Calls `delete_file()` from `utils.py` for any MP3 files that need cleanup

### `/move_to_next` Command

**Purpose**: Move a specified track to play immediately after the current one.

**Parameters**:
- `title`: The title of the track to move

**Business Logic**:
1. Get the queue for the server
2. Find the entry with the matching title
3. Remove it from its current position
4. Insert it at position 1 (after the currently playing track)
5. Update the queue manager

**Example Flow**:
```
User: /move_to_next title: Never Gonna Give You Up
Bot: [defers response]
Bot: [retrieves queue]
Bot: [finds and moves the entry]
Bot: [updates queue manager]
Bot: Moved 'Never Gonna Give You Up' to the second position in the queue.
```

**Implementation Details**:
- The command is defined in `commands.py` in the `move_to_next()` method
- The business logic is implemented in `command_functions.py` in the `process_move_to_next()` function
- Uses `next()` with a generator expression to find the matching entry
- Uses `pop()` and `insert()` to move the entry

### `/search_and_play_from_queue` Command

**Purpose**: Search the current queue and play the specified track.

**Parameters**:
- `title`: The title of the track to search for and play

**Business Logic**:
1. Get the queue for the server
2. Find the entry with the matching title
3. Remove it from its current position
4. Insert it at position 0 (making it the next to play)
5. Stop the current playback
6. Play the selected track

**Example Flow**:
```
User: /search_and_play_from_queue title: Never Gonna Give You Up
Bot: [defers response]
Bot: [retrieves queue]
Bot: [finds and moves the entry to position 0]
Bot: [stops current playback]
Bot: [starts playing the selected track]
Bot: Now playing 'Never Gonna Give You Up'
```

**Implementation Details**:
- The command is defined in `commands.py` in the `search_and_play_from_queue()` method
- The business logic is implemented in `command_functions.py` in the `process_search_and_play_from_queue()` function
- Uses `next()` with a generator expression to find the matching entry
- Uses `pop()` and `insert()` to move the entry
- Calls `voice_client.stop()` to stop current playback
- Calls `playback_manager.play_audio()` to start playing the selected track

## MP3 Management Commands

### MP3 File Handling

The bot supports uploading, playing, and managing MP3 files. These files are stored in the `downloaded-mp3s` directory and can be managed with the following commands.

### `.mp3_list` Command

**Purpose**: Upload and queue MP3 files.

**Business Logic**:
1. Check if the bot is in a voice channel, connecting if needed
2. Process any attached MP3 files
3. For each file:
   - Download the file to the `downloaded-mp3s` directory
   - Extract metadata (title, duration, etc.)
   - Create a queue entry
   - Add the entry to the queue
4. If nothing is playing, start playback of the first entry

**Example Flow**:
```
User: .mp3_list [attaches MP3 files]
Bot: [connects to voice channel if needed]
Bot: [downloads MP3 files]
Bot: [extracts metadata]
Bot: [adds entries to queue]
Bot: 'Song Title 1' added to the queue.
Bot: 'Song Title 2' added to the queue.
Bot: [starts playback if nothing is playing]
```

**Implementation Details**:
- The command is defined in `commands.py` in the `mp3_list()` method
- The business logic is implemented in `command_functions.py` in the `process_mp3_list()` function
- Uses `download_file()` from `utils.py` to download the files
- Uses `extract_mp3_metadata()` from `utils.py` to extract metadata
- Calls `queue_manager.add_to_queue()` to add entries to the queue
- Calls `playback_manager.play_audio()` to start playback if needed

### `.mp3_list_next` Command

**Purpose**: Upload MP3 files and queue them to play next.

**Business Logic**:
1. Check if the bot is in a voice channel, connecting if needed
2. Process any attached MP3 files
3. For each file:
   - Download the file to the `downloaded-mp3s` directory
   - Extract metadata (title, duration, etc.)
   - Create a queue entry
   - Insert the entry at the next position in the queue
4. If nothing is playing, start playback of the first entry

**Example Flow**:
```
User: .mp3_list_next [attaches MP3 files]
Bot: [connects to voice channel if needed]
Bot: [downloads MP3 files]
Bot: [extracts metadata]
Bot: [inserts entries at position 1+ in queue]
Bot: 'Song Title 1' added to the queue at position 2.
Bot: 'Song Title 2' added to the queue at position 3.
Bot: [starts playback if nothing is playing]
```

**Implementation Details**:
- The command is defined in `commands.py` in the `mp3_list_next()` method
- The business logic is implemented in `command_functions.py` in the `process_mp3_list_next()` function
- Similar to `.mp3_list` but inserts at position 1+ instead of appending

## Additional Features

### `/lyrics` Command

**Purpose**: Display lyrics for the current song or a specified query.

**Parameters**:
- `query` (optional): The song to search lyrics for

**Business Logic**:
1. If no query is provided, use the currently playing song
2. Search for lyrics using the Genius API
3. Format and send the lyrics to the user

**Example Flow**:
```
User: /lyrics
Bot: [defers response]
Bot: [gets currently playing song]
Bot: [searches for lyrics]
Bot: [formats lyrics]
Bot: [sends lyrics as message]
```

**Implementation Details**:
- The command is defined in `commands.py`
- The business logic is implemented in `command_functions.py`
- Uses the Genius API through the `lyricsgenius` library
- Formats lyrics to remove unnecessary text and fit within Discord's message limits

### `/discover` Command

**Purpose**: Discover and queue similar songs based on the current track.

**Parameters**:
- `artist_or_song` (optional): Artist or song to use as seed

**Business Logic**:
1. If no parameter is provided, use the currently playing song
2. Extract the artist name from the song title
3. Search for similar artists using the Last.fm API
4. Get top tracks for those artists
5. Search YouTube for those tracks
6. Add them to the queue

**Example Flow**:
```
User: /discover
Bot: [defers response]
Bot: [gets currently playing song]
Bot: [extracts artist name]
Bot: [searches for similar artists]
Bot: [gets top tracks]
Bot: [searches YouTube for tracks]
Bot: [adds tracks to queue]
Bot: Discovery complete! Added 8 tracks to the queue.
```

**Implementation Details**:
- The command is defined in `commands.py` in the `discover()` method
- The business logic is implemented in `command_functions.py` in the `discover_and_queue_recommendations()` function
- Uses the Last.fm API to find similar artists and their top tracks
- Uses the same YouTube search functionality as the `/play` command to find and queue tracks

## Command Interactions

Commands interact with each other through the shared queue and playback managers. Here are some common interaction patterns:

### Queue Modification Interactions

1. **Adding to Queue**: Commands like `/play`, `/play_next_in_queue`, and `.mp3_list` add entries to the queue.
2. **Removing from Queue**: Commands like `/remove_by_title`, `/remove_queue`, and `/clear_queue` remove entries from the queue.
3. **Reordering Queue**: Commands like `/shuffle`, `/move_to_next`, and `/search_and_play_from_queue` change the order of entries in the queue.

### Playback Control Interactions

1. **Starting Playback**: Commands like `/play`, `/play_queue`, and `/search_and_play_from_queue` start playback.
2. **Pausing/Resuming**: Commands like `/pause` and `/resume` control the playback state.
3. **Stopping Playback**: Commands like `/stop` and `/skip` stop playback.
4. **Restarting Playback**: The `/restart` command restarts the current track.

### State Management Interactions

1. **Queue State**: The queue manager maintains the state of the queue for each server.
2. **Playback State**: The playback manager maintains the state of the currently playing track.
3. **Now Playing Interface**: Multiple commands update the now playing interface.

## Error Handling

The bot implements comprehensive error handling throughout the command flow:

1. **Input Validation**: Commands validate user input before processing.
2. **API Error Handling**: Errors from external APIs (YouTube, Genius, Last.fm) are caught and reported.
3. **Playback Error Recovery**: If a track fails to play, the bot attempts to play the next track.
4. **File Operation Safety**: File operations include error handling to prevent crashes.
5. **Asynchronous Error Handling**: All async functions include try/except blocks to catch errors.

### Error Handling Flow Example

```
User: /play youtube_url: https://invalid-url.com
Bot: [defers response]
Bot: [attempts to process URL]
Bot: [catches error in yt_dlp]
Bot: [logs error]
Bot: An error occurred while processing the URL: No video found at the provided URL.
```

This comprehensive documentation covers all the commands, their business logic, and how they interact with each other and the underlying systems. It provides a clear understanding of the bot's functionality and can serve as a reference for users and developers alike.
