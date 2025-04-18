# Discord Radio Bot - User Guide

Welcome to the Discord Radio Bot! This guide will help you understand how to use all the features of this versatile audio player for your Discord server.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Commands](#basic-commands)
3. [Queue Management](#queue-management)
4. [Playback Controls](#playback-controls)
5. [Interactive Buttons](#interactive-buttons)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### Inviting the Bot

To add the Discord Radio Bot to your server:

1. Ensure you have the "Manage Server" permission
2. Use the bot's invite link (provided by the bot owner)
3. Select your server and authorize the bot
4. The bot requires the following permissions:
   - View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Add Reactions
   - Connect to Voice Channels
   - Speak in Voice Channels
   - Use Application Commands

### First Steps

1. Join a voice channel
2. Use the `/play` command with a YouTube URL or search term
3. The bot will join your channel and begin playing audio
4. Use the interactive buttons or commands to control playback

## Basic Commands

The bot supports both slash commands (/) and some custom dot commands (.).

### Essential Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/play` | Play audio from YouTube or MP3 | `/play https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| `/skip` | Skip to the next track | `/skip` |
| `/stop` | Stop playback and disconnect | `/stop` |
| `/list_queue` | Show the current queue | `/list_queue` |

### Playing Audio

The `/play` command is versatile and accepts:

- YouTube URLs (videos or playlists)
- Search terms (the bot will search YouTube)
- MP3 file attachments

Examples:
```
/play https://www.youtube.com/watch?v=dQw4w9WgXcQ
/play never gonna give you up
/play [attach an MP3 file]
```

## Queue Management

The bot maintains a queue of tracks to play. Here's how to manage it:

### Adding to Queue

| Command | Description | Example |
|---------|-------------|---------|
| `/play` | Add to the end of queue | `/play despacito` |
| `/play_next` | Add as next track to play | `/play_next despacito` |
| `.mp3_list` | Add multiple MP3s or URLs | `.mp3_list [attach multiple MP3s]` |

### Viewing the Queue

Use `/list_queue` to see all tracks in the current queue. This will show:
- Track titles
- Duration
- Who has favorited each track
- URLs for YouTube tracks

### Removing from Queue

| Command | Description | Example |
|---------|-------------|---------|
| `/remove_queue` | Remove by position | `/remove_queue 3` |
| `/remove_by_title` | Remove by title | `/remove_by_title Despacito` |
| `/clear_queue` | Clear entire queue | `/clear_queue` |

### Reordering the Queue

Use the interactive buttons on the "Now Playing" message to:
- Move tracks up
- Move tracks down
- Move tracks to top
- Move tracks to bottom
- Shuffle the entire queue

## Playback Controls

### Basic Controls

| Command | Description |
|---------|-------------|
| `/play` | Start playback |
| `/skip` | Skip to next track |
| `/stop` | Stop playback and disconnect |
| `/restart` | Restart current track |
| `/previous` | Play the previous track |

### Playback Modes

| Feature | Description | How to Use |
|---------|-------------|------------|
| Loop | Repeat the current track | Click the loop button |
| Favorites | Mark tracks you like | Click the star button |

## Interactive Buttons

The bot provides an interactive "Now Playing" message with buttons for easy control:

### Button Controls

| Button | Function |
|--------|----------|
| ⏯️ | Pause/Resume playback |
| ⏭️ | Skip to next track |
| ⏹️ | Stop playback |
| 🔄 | Restart current track |
| ⏮️ | Play previous track |
| 🔁 | Toggle loop mode |
| ⭐ | Favorite current track |
| ❌ | Remove from queue |
| 📜 | Show queue list |
| 🔀 | Shuffle queue |
| ⬆️ | Move track up |
| ⬇️ | Move track down |
| ⏫ | Move track to top |
| ⏬ | Move track to bottom |

### Progress Bar

The "Now Playing" message includes a progress bar showing:
- Current playback position
- Total track duration
- Visual progress indicator

## Advanced Features

### Search and Play

| Command | Description | Example |
|---------|-------------|---------|
| `/search_youtube` | Search YouTube and add to queue | `/search_youtube synthwave mix` |
| `/search_and_play_from_queue` | Find and play from queue | `/search_and_play_from_queue despacito` |

### Playlist Support

The bot fully supports YouTube playlists:
- Use `/play` with a playlist URL
- The first track plays immediately
- Remaining tracks are added to queue
- Progress updates as tracks are processed

Example:
```
/play https://www.youtube.com/playlist?list=PLw-VjHDlEOgvtnnnqWlTqByAtC7tXBg6D
```

### MP3 List Support

To play multiple MP3 files:
1. Use the `.mp3_list` command
2. Attach multiple MP3 files to your message
3. The bot will process and queue all files

You can also include YouTube URLs in the message text.

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Bot doesn't join voice channel | Make sure you're in a voice channel first |
| Bot doesn't respond to commands | Check if the bot has proper permissions |
| Audio quality issues | Try a different source or URL |
| YouTube URL doesn't work | The bot now handles all YouTube URLs including age-restricted content |
| Bot disconnects unexpectedly | Check your internet connection and Discord server status |

### Getting Help

If you encounter issues not covered in this guide:
- Check the bot's status messages
- Contact the server administrator
- Check the bot's GitHub repository for updates

## Command Reference

### All Available Commands

| Command | Description |
|---------|-------------|
| `/play` | Play audio from YouTube URL, search term, or MP3 attachment |
| `/play_next` | Add audio to play immediately after current track |
| `/skip` | Skip to the next track in queue |
| `/stop` | Stop playback and disconnect from voice channel |
| `/restart` | Restart the current track from beginning |
| `/previous` | Return to the previously played track |
| `/shuffle` | Randomize the queue order |
| `/list_queue` | Display the current queue |
| `/clear_queue` | Remove all tracks from queue except current |
| `/remove_queue` | Remove a track by its position in queue |
| `/remove_by_title` | Remove a track by its title |
| `/search_youtube` | Search YouTube and add result to queue |
| `/search_and_play_from_queue` | Find and play a track from queue |
| `.mp3_list` | Process multiple MP3 files or YouTube URLs |

Enjoy your Discord Radio Bot experience!
