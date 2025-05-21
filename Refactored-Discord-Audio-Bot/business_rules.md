# Discord Radio Bot - Business Rules Documentation

This document outlines the business logic and rules implemented in the Discord Radio Bot. It serves as a comprehensive reference for understanding how the bot functions, its capabilities, and the underlying logic that governs its behavior.

## Table of Contents

1. [Core Components](#core-components)
2. [Queue Management](#queue-management)
3. [Playback Control](#playback-control)
4. [Media Source Handling](#media-source-handling)
5. [User Interaction](#user-interaction)
6. [Error Handling](#error-handling)
7. [Persistence](#persistence)
8. [Command Structure](#command-structure)
9. [Potential Abuse Cases](#potential-abuse-cases)

## Core Components

The Discord Radio Bot is built with a modular architecture consisting of several key components:

### PlaybackManager
- Responsible for audio playback functionality
- Handles streaming from various sources (YouTube, MP3 files)
- Manages playback state (playing, paused, stopped)
- Implements playback controls (play, pause, resume, skip, etc.)
- Handles URL extraction and processing

### QueueManager
- Maintains server-specific audio queues
- Tracks currently playing audio
- Manages queue operations (add, remove, shuffle, etc.)
- Persists queue state to disk

### ButtonView
- Provides interactive UI elements for controlling playback
- Implements button callbacks for various actions
- Displays "Now Playing" information with progress bars

### Command Handlers
- Processes slash commands and dot commands
- Routes commands to appropriate functions
- Validates user input and permissions

## Queue Management

### Queue Structure
- Each server has its own independent queue
- Queues are stored as lists of QueueEntry objects
- Queue state is persisted to disk in JSON format
- Queue entries contain metadata (title, URL, duration, etc.)

### Queue Entry Lifecycle
1. Entry is created when a user requests audio playback
2. Entry is added to the queue (either at the end or a specific position)
3. When the entry reaches the front of the queue, it begins playing
4. After playback completes, the entry is either:
   - Removed from the queue (default behavior)
   - Moved to the end of the queue (if looping is enabled)
   - Kept in place (if restarting)

### Queue Manipulation Rules
- Users can add entries to the queue via `/play`, `/play_next`, or `.mp3_list`
- Users can remove entries via `/remove_queue`, `/remove_by_title`, or the remove button
- Users can reorder the queue via move up/down/top/bottom buttons
- Users can clear the queue via `/clear_queue`
- Users can shuffle the queue via `/shuffle`
- The currently playing entry is protected from certain operations

## Playback Control

### Playback States
- **Playing**: Audio is currently being streamed
- **Paused**: Playback is temporarily halted but can resume
- **Stopped**: Playback is completely halted and voice connection may be disconnected

### Playback Control Rules
- Only one audio stream can play at a time per server
- Playback automatically advances to the next queue entry when current playback ends
- Users can control playback via buttons or slash commands
- Playback can be paused and resumed without losing position
- Skipping immediately ends current playback and starts the next entry
- Stopping ends playback and may disconnect from voice channel
- Restarting replays the current entry from the beginning

### Looping Behavior
- When loop is enabled, the current track repeats after finishing
- Loop state is toggled via the loop button
- Loop state is maintained per server

## Media Source Handling

### Supported Media Sources
- YouTube videos (single videos)
- YouTube playlists
- MP3 files (uploaded as attachments)
- MP3 URLs (direct links to MP3 files)

### YouTube URL Processing
- YouTube URLs are processed using yt-dlp
- The bot extracts metadata (title, duration, thumbnail)
- The bot extracts the best audio stream URL
- Age-restricted content is handled with special options
- Bot detection is bypassed using user agent impersonation
- Multiple fallback mechanisms ensure maximum compatibility

### MP3 Processing
- MP3 files are downloaded to a local directory
- Metadata is extracted from ID3 tags when available
- Files are cleaned up when no longer needed

### Playlist Handling
- Playlists are processed incrementally
- The first video starts playing immediately
- Remaining videos are added to the queue asynchronously
- Unavailable videos in playlists are skipped with notifications

## User Interaction

### Now Playing Display
- Shows current track information (title, thumbnail)
- Displays a progress bar that updates in real-time
- Shows favorite status
- Provides interactive buttons for playback control

### Button Controls
- **Pause/Resume**: Toggles playback state
- **Skip**: Advances to the next track
- **Stop**: Ends playback
- **Restart**: Replays current track from beginning
- **Previous**: Returns to the last played track
- **Loop**: Toggles repeat mode for current track
- **Favorite**: Marks track as a favorite
- **Remove**: Removes track from queue
- **Move Up/Down/Top/Bottom**: Repositions track in queue
- **Shuffle**: Randomizes queue order
- **List Queue**: Displays current queue

### Favoriting System
- Users can mark tracks as favorites
- Favorite status is stored with the track
- Favorites are displayed in the Now Playing message
- Favorite status persists across sessions

## Error Handling

### Playback Errors
- Network errors are handled with retries
- Unavailable videos are reported to users
- Age-restricted content is handled with special options
- Bot detection is bypassed using multiple techniques
- Playback errors are logged for troubleshooting

### Command Errors
- Invalid commands are reported to users
- Missing permissions are handled gracefully
- Missing arguments trigger appropriate error messages
- Execution errors are logged and reported

### Recovery Mechanisms
- Connection issues trigger reconnection attempts
- Stream errors may trigger URL refresh
- Aggressive options are used as fallbacks
- Default values are used when metadata cannot be retrieved

## Persistence

### Persistent Data
- Queue state (stored in queues.json)
- Last played audio (stored in last_played_audio.json)
- Downloaded MP3 files (stored in downloaded-mp3s directory)

### Persistence Rules
- Queue state is saved after every modification
- Last played audio is updated when tracks finish playing
- Downloaded files are cleaned up when no longer in any queue
- Persistence ensures state is maintained across bot restarts

## Command Structure

### Slash Commands
- `/play`: Plays audio from YouTube URL, search term, or MP3 attachment
- `/play_next`: Adds audio to play immediately after current track
- `/skip`: Skips to the next track in queue
- `/stop`: Stops playback and disconnects from voice channel
- `/restart`: Restarts the current track from beginning
- `/previous`: Returns to the previously played track
- `/shuffle`: Randomizes the queue order
- `/list_queue`: Displays the current queue
- `/clear_queue`: Removes all tracks from queue except current
- `/remove_queue`: Removes a track by its position in queue
- `/remove_by_title`: Removes a track by its title
- `/search_and_play_from_queue`: Finds and plays a track from queue

### Dot Commands
- `.mp3_list`: Processes multiple MP3 files or YouTube URLs

## Potential Abuse Cases

### Resource Consumption
- **Issue**: Users could queue extremely long videos or large playlists
- **Mitigation**: Implement queue size limits per user or server

### API Rate Limiting
- **Issue**: Excessive YouTube requests could trigger rate limiting
- **Mitigation**: Implement request throttling and caching

### Inappropriate Content
- **Issue**: Users could play inappropriate or offensive content
- **Mitigation**: Implement content filtering or moderation features

### Command Spam
- **Issue**: Users could spam commands to disrupt bot operation
- **Mitigation**: Implement command cooldowns and user-specific rate limits

### Voice Channel Abuse
- **Issue**: Users could force the bot to rapidly join/leave channels
- **Mitigation**: Implement cooldowns on voice channel operations

### Long-Running Sessions
- **Issue**: Bot could be left in voice channels indefinitely
- **Mitigation**: Implement auto-disconnect after period of inactivity
