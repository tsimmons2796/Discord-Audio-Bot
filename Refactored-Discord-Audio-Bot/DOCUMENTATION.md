# Off-Brand Pandora Implementation Documentation

## Overview

This document provides a comprehensive overview of the `/off_brand_pandora` command implementation for the Discord Audio Bot. The command creates a Pandora-like music discovery experience by recommending and queueing tracks based on mood, genre, or the currently playing song.

## Features

1. **Multiple Recommendation Sources**:
   - Uses the currently playing song's artist as a seed for recommendations
   - Supports mood-based music discovery (e.g., happy, chill, sad)
   - Supports genre-based music discovery (e.g., rock, electronic, jazz)
   - Combines multiple sources for better recommendations

2. **Robust Error Handling**:
   - Gracefully handles missing or invalid parameters
   - Provides fallback mechanisms when primary recommendation sources fail
   - Properly handles edge cases like "Various Artists" or "[unknown]" artists

3. **Memory Management**:
   - Tracks and manages recommendation tasks per guild
   - Cancels and replaces existing tasks when a new command is issued
   - Prevents memory leaks and resource exhaustion

4. **Enhanced YouTube Integration**:
   - Bypasses age restrictions and bot detection mechanisms
   - Uses aggressive fallback options when standard approaches fail
   - Properly handles YouTube search results

5. **User Experience**:
   - Provides meaningful feedback to users
   - Queues tracks without interrupting ongoing playback
   - Deduplicates recommendations to avoid repetition

## Implementation Details

### Command Structure

The `/off_brand_pandora` command accepts two optional parameters:
- `mood`: A string representing the desired mood (e.g., happy, chill, sad)
- `genres`: A comma-separated list of genres (e.g., rock,electronic,jazz)

If neither parameter is provided, the command will use the currently playing song as a seed for recommendations.

### Recommendation Flow

1. **Seed Artist Identification**:
   - If a song is currently playing, extract the artist name
   - Skip problematic artists like "Various Artists" or "[unknown]"

2. **Similar Artist Discovery**:
   - Query MusicBrainz API to find artists similar to the seed artist
   - Filter out problematic artists from the results

3. **Track Collection**:
   - For each similar artist, collect their top tracks
   - Store tracks in a set to avoid duplicates

4. **Mood/Genre Enrichment**:
   - If mood or genres are provided, find artists associated with those tags
   - Add tracks from these artists to the recommendation set

5. **YouTube Search**:
   - For each recommended track, search YouTube for the best match
   - Use enhanced options to bypass restrictions
   - Queue the track using the `process_play` function

### Memory Management

The implementation uses a dictionary (`bot.pandora_tasks`) to track active recommendation tasks per guild. When a new command is issued, any existing task for that guild is cancelled before starting a new one. This prevents resource leaks and ensures that only one recommendation task is active per guild at any time.

### Error Handling

The implementation includes comprehensive error handling at each step of the process:
- MusicBrainz API errors are caught and logged
- YouTube search errors are caught and the process continues with the next track
- If no recommendations are found, a meaningful message is sent to the user

## Usage Examples

1. **Mood-based discovery**:
   ```
   /off_brand_pandora mood:happy
   ```

2. **Genre-based discovery**:
   ```
   /off_brand_pandora genres:rock,electronic
   ```

3. **Combined mood and genre**:
   ```
   /off_brand_pandora mood:chill genres:jazz,lofi
   ```

4. **Based on current song**:
   ```
   /off_brand_pandora
   ```

## Technical Considerations

- The implementation uses rate limiting to avoid overwhelming the MusicBrainz API
- YouTube searches are performed sequentially to avoid rate limiting issues
- The command is designed to work asynchronously to prevent blocking the bot's event loop
