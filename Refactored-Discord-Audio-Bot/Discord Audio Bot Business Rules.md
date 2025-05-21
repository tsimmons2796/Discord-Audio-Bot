# Discord Audio Bot Business Rules

This document outlines the detailed business logic and rules implemented in the Discord Audio Bot, based on the actual codebase implementation.

## Command Structure

### 1. Dual Command Interface System

1.1. **Slash Commands**
   - All commands are registered as Discord application commands via `app_commands.command` decorators
   - Commands support parameter auto-completion where applicable (e.g., track titles)
   - All slash commands defer their response with `interaction.response.defer()` to allow for longer processing time
   - Command responses use followup messages to provide feedback after processing

1.2. **Custom Dot Commands**
   - A subset of commands is also available as message-based commands prefixed with a dot (`.`)
   - Specifically implemented for: `.mp3_list`, `.mp3_list_next`, and `.listen`
   - Dot commands are processed in the `on_message` event handler in `bot.py`
   - Command context is created with `await self.get_context(message)` and executed with `await self.invoke(ctx)`

1.3. **Command Consistency**
   - All commands maintain consistent behavior regardless of which interface is used to invoke them
   - Command logic is centralized in the `command_functions.py` module to ensure consistency
   - Both interfaces use the same underlying queue and playback management systems

## Audio Queue Management

### 2. Queue System

2.1. **Server-Specific Queues**
   - Each Discord server (guild) has its own independent queue stored by server ID
   - Queues are persisted to disk in `queues.json` to survive bot restarts
   - Queue entries are serialized to JSON using the `to_dict()` method and deserialized using `from_dict()`
   - The `BotQueue.ensure_queue_exists(server_id)` method creates an empty queue if none exists

2.2. **Queue Entry Structure**
   - Each queue entry (`QueueEntry` class) contains:
     - `video_url`: Original source URL
     - `best_audio_url`: Direct audio stream URL
     - `title`: Sanitized track title
     - `is_playlist`: Boolean flag indicating if part of a playlist
     - `playlist_index`: Position in original playlist (if applicable)
     - `thumbnail`: URL to thumbnail image
     - `duration`: Track duration in seconds
     - `is_favorited`: Boolean flag for favorite status
     - `favorited_by`: List of users who favorited the track
     - `has_been_arranged`: Flag indicating if track position was manually changed
     - `has_been_played_after_arranged`: Flag tracking if arranged track was played
     - `timestamp`: ISO-formatted creation time
     - `paused_duration`: Cumulative time the track was paused
     - `guild_id`: Server ID where the track is queued
     - `pause_start_time`: Timestamp when pause was initiated
     - `start_time`: Timestamp when playback started

2.3. **Queue Validation**
   - The `validate_queue(server_id)` method verifies queue integrity before saving
   - Validation checks that all entries are proper `QueueEntry` instances
   - Failed validation prevents queue from being saved to avoid data corruption

2.4. **Queue Persistence**
   - Queues are automatically saved to disk after any modification
   - The `save_queues()` method writes to `queues.json` and `last_played_audio.json`
   - A queue cache is maintained to improve performance for frequent queue access
   - The `load_queues()` method restores queues from disk on bot startup

2.5. **Queue Manipulation**
   - Tracks can be added to the end of the queue with `add_to_queue(server_id, entry)`
   - Tracks can be inserted at position 2 (after currently playing) with the `play_next` command
   - Tracks can be removed by index or by title
   - The queue can be cleared except for the currently playing track
   - Duplicate tracks can be removed based on title comparison

## Audio Playback Rules

### 3. Playback Management

3.1. **Voice Channel Connection**
   - Users must be in a voice channel to request audio playback
   - The bot automatically joins the user's voice channel when a playback command is issued
   - If the user is not in a voice channel, an error message is sent
   - The bot maintains a single voice client connection per server

3.2. **Playback Control**
   - The `PlaybackManager` class handles all audio playback operations
   - Audio is played using Discord's `FFmpegPCMAudio` with PCM volume transformation
   - Default volume is set to 75% (0.75) when playback starts
   - Volume can be adjusted during playback
   - Playback state (playing/paused) is tracked in the queue manager

3.3. **Playback Queue Processing**
   - When a track finishes playing, the `after_playing_callback` is triggered
   - If looping is enabled, the same track plays again
   - Otherwise, the track is moved to the end of the queue if it hasn't been arranged
   - The next track in the queue is automatically played
   - If a track has been manually arranged and played, its arrangement flags are reset

3.4. **Auto-Disconnect**
   - The bot automatically leaves a voice channel after a configurable period of inactivity
   - This is handled by the voice state update event in Discord.py

3.5. **Playback State Persistence**
   - The currently playing track is tracked in the queue manager
   - Pause state is persisted between commands
   - Track position is calculated based on start time, current time, and cumulative pause duration
   - This allows the progress bar to accurately reflect playback position

### 4. Track Source Handling

4.1. **YouTube URL Processing**
   - YouTube URLs are processed using `yt_dlp` with specific options:
     - `format: 'bestaudio/best'` to get highest quality audio
     - `noplaylist: True/False` depending on whether a playlist is detected
     - Custom user agent and headers to avoid bot detection
     - Cookie file support for age-restricted content
   - Both standard and shortened YouTube URLs are supported
   - Playlist URLs are detected by checking for `list=` in the URL

4.2. **YouTube Title Search**
   - When a title is provided instead of a URL, the bot searches YouTube
   - Search uses `ytsearch5:` prefix to get multiple results
   - Results are filtered to avoid duplicates already in the queue
   - Videos longer than 10 minutes (600 seconds) are skipped
   - If all results are duplicates, alternative search strategies are attempted:
     - Appending "official audio", "official video", "lyrics", etc.
     - Searching for other tracks by the same artist via Last.fm
     - Searching for tracks by similar artists

4.3. **MP3 File Handling**
   - MP3 files can be uploaded as Discord attachments
   - Files are downloaded to the `downloaded-mp3s` directory
   - Metadata is extracted from the MP3 file for title, duration, etc.
   - Local file path is used as the audio source URL

4.4. **Playlist Processing**
   - When a playlist URL is detected, only the first video is processed immediately
   - The rest of the playlist is processed asynchronously in the background
   - Each video in the playlist is checked for availability before adding to the queue
   - Unavailable videos are skipped with a notification
   - Progress updates are sent as videos are added to the queue

## Now Playing Interface

### 5. Visual Interface

5.1. **Now Playing Embed**
   - The bot displays a rich embed for the currently playing track containing:
     - Track title with link to source
     - Thumbnail image
     - Progress bar showing current position
     - Duration information (elapsed/total)
     - Queue position information
   - The embed is automatically updated every 5 seconds to reflect playback progress
   - Updates are scheduled using `asyncio.create_task()`

5.2. **Interactive Controls**
   - The `ButtonView` class provides interactive buttons for playback control
   - Buttons are dynamically added based on the current context
   - Button styles change to reflect current state (e.g., Loop button changes when active)
   - Custom IDs are generated with UUID to ensure uniqueness

5.3. **Available Controls**
   - **Playback Controls**:
     - Play/Pause toggle
     - Stop (disconnects from voice channel)
     - Skip (moves to next track)
     - Restart (restarts current track)
     - Previous (plays previously played track)
     - Loop toggle (repeats current track)
   - **Queue Management**:
     - List Queue (shows all queued tracks)
     - Shuffle (randomizes queue order)
     - Remove (removes current track)
   - **Track Position Controls**:
     - Move Up (moves track one position earlier)
     - Move Down (moves track one position later)
     - Move to Top (moves track to start of queue)
     - Move to Bottom (moves track to end of queue)
   - **Additional Features**:
     - Favorite (marks track as favorite)
     - Lyrics (fetches and displays lyrics)

5.4. **Progress Bar Updates**
   - Progress bar is implemented as a visual representation of playback position
   - Updates are scheduled using `schedule_progress_bar_update()`
   - Progress calculation accounts for paused time
   - Updates stop when playback ends or track changes

5.5. **Multiple Message Management**
   - Now playing messages are tracked in `bot.now_playing_messages`
   - New messages can be added with `add_now_playing_message(message_id)`
   - All messages can be cleared with `clear_now_playing_messages()`
   - This allows updating all now playing messages when state changes

## YouTube Integration

### 6. YouTube Handling

6.1. **URL Format Support**
   - Standard YouTube URLs (`youtube.com/watch?v=...`)
   - Shortened URLs (`youtu.be/...`)
   - Playlist URLs (`youtube.com/playlist?list=...`)
   - URLs with both video ID and playlist ID
   - URLs with timestamps (ignored during playback)

6.2. **Bot Detection Avoidance**
   - Custom User-Agent header mimicking Chrome browser
   - Cookie file support for authentication
   - Reconnection options for interrupted streams
   - Error handling for rate limiting and unavailable videos

6.3. **Playlist Handling**
   - Single video extraction from playlists when requested
   - Option to process entire playlists
   - Playlist index tracking for proper ordering
   - Asynchronous processing to avoid blocking the bot

6.4. **Age Restriction Handling**
   - Cookie file support to bypass age restrictions when possible
   - Fallback to alternative sources when primary source fails
   - Error messages for content that cannot be accessed

6.5. **YouTube Search**
   - Title search uses `ytsearch5:` prefix to get multiple results
   - Results are filtered for duplicates already in queue
   - Alternative search terms are tried when initial search fails
   - Integration with Last.fm for related content discovery

## Error Handling

### 7. Error Management

7.1. **Command Errors**
   - All commands use try/except blocks to catch and handle errors
   - Specific error messages are sent to users based on error type
   - Errors are logged to command-specific log files
   - Debug information is printed to console during development

7.2. **Playback Errors**
   - Playback errors are caught in the `after_playing_callback`
   - Network interruptions trigger reconnection attempts
   - Unavailable videos are skipped with notification
   - Corrupt or invalid audio sources trigger appropriate error messages

7.3. **Queue Errors**
   - Queue validation prevents saving corrupted queue data
   - Index out of range errors are handled with user-friendly messages
   - Empty queue conditions are checked before operations
   - Duplicate detection prevents adding identical tracks

7.4. **Logging System**
   - Comprehensive logging to multiple log files:
     - `bot.log`: General bot operations
     - `commands.log`: Command execution
     - `playback.log`: Audio playback
     - `queue_manager.log`: Queue operations
     - `views.log`: UI interactions
   - Log levels include DEBUG, INFO, WARNING, ERROR
   - Timestamps are included for all log entries

7.5. **User Feedback**
   - Clear error messages are sent to users
   - Operation success confirmations
   - Progress updates for long-running operations
   - Ephemeral messages for user-specific information

## Security and Privacy

### 8. Security Measures

8.1. **API Token Management**
   - Discord token and other API keys are loaded from environment variables
   - `.env` file is used for local development
   - No hardcoded credentials in the codebase
   - Token validation on startup

8.2. **User Data Handling**
   - Minimal user data is stored (only IDs for favorites)
   - No personal information is retained
   - User data is server-specific
   - Data is only stored for functional purposes

8.3. **Permission Checks**
   - Voice channel membership is verified before playback
   - Administrative commands check for appropriate permissions
   - Button interactions verify the user has permission to use them
   - Guild-specific operations are restricted to the originating guild

8.4. **External Service Integration**
   - API requests use proper authentication
   - Rate limiting is respected
   - Error handling for service unavailability
   - Timeout handling for external requests

## Performance Optimization

### 9. Resource Management

9.1. **Memory Usage**
   - Queue caching to reduce disk I/O
   - Efficient data structures for queue management
   - Proper cleanup of resources after use
   - Garbage collection of unused objects

9.2. **CPU Utilization**
   - Asynchronous processing for non-blocking operations
   - Thread pool executor for CPU-bound tasks
   - Efficient algorithms for queue manipulation
   - Optimized audio processing

9.3. **Network Efficiency**
   - Buffering for audio streams
   - Reconnection logic for interrupted streams
   - Caching of frequently accessed data
   - Batched updates for UI elements

9.4. **Disk I/O**
   - Queue persistence with efficient serialization
   - File handling with proper resource cleanup
   - Temporary file management for downloads
   - Error handling for disk operations

## External Service Integration

### 10. Third-Party Services

10.1. **Last.fm Integration**
   - Artist and track information retrieval
   - Similar artist discovery
   - Top track recommendations
   - Error handling for API unavailability

10.2. **Genius Lyrics Integration**
   - Lyrics fetching for currently playing tracks
   - Search by artist and title
   - Fallback mechanisms for missing lyrics
   - Formatting for Discord message limits

10.3. **Spotify Integration (Optional)**
   - Track discovery and recommendations
   - Playlist import capabilities
   - Authentication and authorization handling
   - Rate limit and quota management

10.4. **MusicBrainz Integration (Optional)**
   - Metadata enhancement for tracks
   - Artist and album information
   - Release date and genre data
   - Proper user agent identification

## Command-Specific Rules

### 11. Playback Commands

11.1. **Play Command**
   - Accepts YouTube URL, YouTube title search, or MP3 file
   - Joins user's voice channel if not already connected
   - Adds track to end of queue if something is already playing
   - Starts playback immediately if queue is empty
   - Handles playlists by adding all tracks to queue
   - Provides feedback on successful queue addition

11.2. **Play Next Command**
   - Similar to Play but inserts track at position 2 in queue
   - If nothing is playing, behaves like regular Play
   - Provides feedback confirming position in queue
   - Supports same input types as Play command

11.3. **Skip Command**
   - Stops current track and moves to next in queue
   - Updates Now Playing interface for new track
   - Provides feedback when no next track is available
   - Handles edge case of last track in queue

11.4. **Pause/Resume Commands**
   - Toggles playback state between playing and paused
   - Updates UI to reflect current state
   - Tracks pause duration for progress calculation
   - Provides visual feedback via button state

11.5. **Stop Command**
   - Stops playback completely
   - Disconnects from voice channel
   - Clears currently playing track
   - Sets stop flag to prevent automatic next track

11.6. **Restart Command**
   - Restarts currently playing track from beginning
   - Resets progress bar and elapsed time
   - Sets restart flag to handle queue properly
   - Updates Now Playing interface

11.7. **Previous Command**
   - Plays the last track that was playing
   - Retrieved from last_played_audio.json
   - Provides feedback if no previous track exists
   - Updates Now Playing interface

### 12. Queue Management Commands

12.1. **List Queue Command**
   - Displays all tracks in current server's queue
   - Shows position, title, and duration
   - Handles pagination for long queues
   - Indicates currently playing track

12.2. **Remove Queue Command**
   - Removes track at specified index
   - Adjusts queue order accordingly
   - Provides feedback on successful removal
   - Handles index out of range errors

12.3. **Remove by Title Command**
   - Searches queue for tracks matching title
   - Removes first matching track
   - Case-insensitive matching
   - Provides feedback if no match found

12.4. **Clear Queue Command**
   - Removes all tracks except currently playing
   - Confirms number of tracks removed
   - Preserves currently playing track
   - Updates queue display if open

12.5. **Shuffle Command**
   - Randomizes order of tracks in queue
   - Preserves currently playing track at position 0
   - Sets shuffle flag to handle queue management
   - Provides feedback on shuffle completion

12.6. **Move to Next Command**
   - Moves specified track to position 2 in queue
   - Uses title autocomplete for track selection
   - Sets arrangement flags for proper queue handling
   - Provides feedback on successful move

12.7. **Search and Play from Queue Command**
   - Searches current queue for matching title
   - Moves matching track to position 0 and plays it
   - Uses title autocomplete for suggestions
   - Provides feedback if no match found

12.8. **Remove Duplicates Command**
   - Scans queue for tracks with identical titles
   - Keeps first occurrence, removes others
   - Case-insensitive comparison
   - Reports number of duplicates removed

### 13. Discovery Commands

13.1. **Discover Command**
   - Finds related tracks based on current or specified track
   - Uses Last.fm API for recommendations
   - Avoids adding duplicates to queue
   - Provides feedback on discovery source and results
   - Supports optional artist/song parameter

## Button-Specific Rules

### 14. Button Interactions

14.1. **Button Creation**
   - Each button has a unique UUID-based custom ID
   - Buttons have appropriate labels and styles
   - Buttons are dynamically added based on context
   - Button callbacks are registered during view initialization

14.2. **Button Visibility Rules**
   - Move Up/Top buttons only show if track isn't first in queue
   - Move Down/Bottom buttons only show if track isn't last in queue
   - Loop button style changes based on loop state
   - Favorite button style changes based on favorite status

14.3. **Button Permission Checks**
   - All button interactions verify the user has appropriate permissions
   - Users can only favorite tracks in servers they belong to
   - Queue manipulation requires voice channel membership
   - Administrative actions check for proper permissions

14.4. **Button Update Mechanism**
   - Button views are refreshed after state changes
   - All now playing messages are updated when applicable
   - Button states reflect current system state
   - Progress updates continue after button interactions

## Edge Cases and Special Handling

### 15. Edge Case Management

15.1. **Empty Queue Handling**
   - Commands that require a non-empty queue provide appropriate feedback
   - UI elements adjust when queue is empty
   - Playback stops naturally when queue is exhausted
   - Clear messaging when operations cannot be performed

15.2. **Disconnection Handling**
   - Bot attempts to reconnect on network interruption
   - Playback state is preserved when possible
   - Error messages for permanent disconnections
   - Queue is preserved for later reconnection

15.3. **Invalid Input Handling**
   - URL validation before processing
   - Feedback for unsupported file types
   - Index validation for queue operations
   - Clear error messages for invalid commands

15.4. **Rate Limit Management**
   - Backoff strategies for external API rate limits
   - Queuing of requests to avoid flooding
   - User feedback during throttling
   - Alternative sources when primary is rate-limited

15.5. **Long Content Handling**
   - Pagination for long queue listings
   - Truncation of extremely long track titles
   - Splitting of long messages to fit Discord limits
   - Handling of extremely long audio files
