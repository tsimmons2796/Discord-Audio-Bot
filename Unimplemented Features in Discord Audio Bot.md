# Unimplemented Features in Discord Audio Bot

Based on analysis of the documentation and code, the following features are mentioned or discussed but not fully implemented:

## 1. Spotify API Integration for `/discover` Command

The TODO.md file extensively discusses enhancing the `/discover` command with Spotify API integration, but the current implementation only uses Last.fm:

- **Missing Implementation:**
  - Spotify API authentication and token retrieval
  - Spotify track/artist search functionality
  - Spotify recommendations endpoint integration
  - Genre seed support from Spotify
  - Energy, valence, danceability filters
  - "Surprise me" mode using Spotify's popular/curated lists

- **Current State:**
  - The bot only uses Last.fm for artist similarity and track recommendations
  - The code in `command_functions.py` shows Last.fm implementation but no Spotify API calls

## 2. Lyrics Display Feature

The "Discord Audio Bot - Complete Documentation.md" mentions a Lyrics button feature, but it's not fully implemented:

- **Missing Implementation:**
  - No Lyrics button in the button view implementation
  - No function to fetch and display lyrics using Genius API
  - No handling for displaying long lyrics as file attachments

- **Current State:**
  - The bot has a Genius API token configuration in the documentation
  - The `lyricsgenius` package is mentioned in requirements
  - No actual lyrics fetching or display code exists in the codebase

## 3. Voice Listening Command

The bot.py file references a `.listen` command, but the implementation is minimal:

- **Missing Implementation:**
  - No detailed functionality for voice listening
  - No documentation on what this feature should do
  - Only a placeholder handler in bot.py

- **Current State:**
  - Only logs "voice_listen command triggered" without actual functionality

## 4. Search YouTube Command

The documentation mentions a `/search_youtube` command, but it's not implemented:

- **Missing Implementation:**
  - No `/search_youtube` command in commands.py
  - No corresponding process function in command_functions.py

- **Current State:**
  - YouTube search functionality exists within other commands (like `/play`)
  - No standalone search command that returns results without playing

## 5. Autocomplete for Genres in `/discover`

The TODO.md mentions adding autocomplete for supported Spotify genre tags:

- **Missing Implementation:**
  - No autocomplete function for genre parameters
  - No list of supported genres

- **Current State:**
  - The `/discover` command doesn't have genre autocomplete
  - No genre parameter is defined in the command

## 6. Volume Control

The documentation doesn't explicitly mention volume control, but the code has a partial implementation:

- **Missing Implementation:**
  - No volume command or button
  - No user-facing way to adjust volume

- **Current State:**
  - The bot.py file sets volume to 0.5 (50%) when joining a voice channel
  - No way for users to change this value

## 7. Comprehensive Error Handling

The TESTING.md file mentions error handling tests, but implementation is incomplete:

- **Missing Implementation:**
  - Limited error handling for edge cases
  - No comprehensive handling for YouTube restrictions
  - No fallback mechanisms for all error scenarios

- **Current State:**
  - Basic try/except blocks exist
  - No systematic approach to error handling and recovery

## 8. Mood-based Discovery

The DOCUMENTATION.md mentions mood-based discovery, but it's not implemented:

- **Missing Implementation:**
  - No mood parameter in the `/discover` command
  - No mapping of moods to musical attributes

- **Current State:**
  - The `/discover` command only accepts an optional artist_or_song parameter
  - No mood-based filtering or selection

## 9. Genre-based Discovery

Similar to mood-based discovery:

- **Missing Implementation:**
  - No genres parameter in the `/discover` command
  - No genre-based filtering or selection

- **Current State:**
  - The `/discover` command doesn't support genre filtering

## 10. "Discover More" Button

The TODO.md mentions a "Discover More" button functionality:

- **Missing Implementation:**
  - No button to request more similar tracks
  - No caching of related artists for future expansion

- **Current State:**
  - Users must manually trigger the `/discover` command again

## 11. MP3 File Management

The user_guide.md mentions MP3 file management features that aren't fully implemented:

- **Missing Implementation:**
  - No comprehensive MP3 file management
  - No listing of available MP3 files
  - No browsing or selecting from stored MP3s

- **Current State:**
  - Basic MP3 file playback works
  - No management interface for stored files
