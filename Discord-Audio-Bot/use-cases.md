## Use Cases

### Play a Single Video or MP3 File

- **Command:** `/play [URL or attachment]`
- **Scenario:** A user provides a YouTube URL or attaches an MP3 file.
- **Expected Behavior:** The bot connects to the user's voice channel, adds the entry to the queue, and starts playing the audio. If the queue was empty, it will start playing the added entry immediately. If there are already entries in the queue, the new entry will be added to the end of the queue.
- **Chain of Events:**
  1. **Command Triggered**: `play` command is triggered.
  2. **Process Play Command**:
     - **Function**: `MusicCommands.play`
     - Checks if the voice client is connected or connects if necessary.
     - Calls `process_single_video_or_mp3` or `process_play_command`.
  3. **Fetch Video or MP3 Info**:
     - **Function**: `process_single_video_or_mp3`
     - **Function**: `fetch_info`
     - Retrieves video info from YouTube or processes the MP3 file.
  4. **Create Queue Entry**:
     - **Function**: `QueueEntry.__init__`
     - Creates a `QueueEntry` object with the video or MP3 information.
  5. **Add to Queue**:
     - **Function**: `BotQueue.add_to_queue`
     - Adds the `QueueEntry` to the queue.
  6. **Check Playback State**:
     - If the bot is not already playing, it calls `play_audio` to start playback.
     - If the bot is already playing, the new entry is added to the end of the queue.
     - **Function**: `play_audio`
     - Connects to the voice channel and starts playing the audio.

### Play a Playlist

- **Command:** `/play [playlist URL]`
- **Scenario:** A user provides a YouTube playlist URL.
- **Expected Behavior:** The bot connects to the user's voice channel, adds all videos in the playlist to the queue, and starts playing the first video. Subsequent videos in the playlist will play automatically after the current one finishes.
- **Chain of Events:**
  1. **Command Triggered**: `play` command is triggered.
  2. **Process Play Command**:
     - **Function**: `MusicCommands.play`
     - Checks if the voice client is connected or connects if necessary.
     - Calls `process_play_command`.
  3. **Fetch Playlist Info**:
     - **Function**: `process_play_command`
     - **Function**: `fetch_info`
     - **Function**: `fetch_playlist_length`
     - Retrieves playlist info from YouTube.
  4. **Create Queue Entries**:
     - **Function**: `QueueEntry.__init__`
     - Creates multiple `QueueEntry` objects for each video in the playlist.
  5. **Add to Queue**:
     - **Function**: `BotQueue.add_to_queue`
     - Adds the `QueueEntry` objects to the queue.
  6. **Check Playback State**:
     - If the bot is not already playing, it calls `play_audio` to start playback of the first video.
     - If the bot is already playing, the playlist entries are added to the end of the queue.
     - **Function**: `play_audio`

### Pause and Resume Playback

- **Button:** ⏸️ Pause / ▶️ Resume
- **Scenario:** A user pauses and then resumes the playback.
- **Expected Behavior:** The bot pauses the current track and resumes playback when the resume button is clicked. The playback should continue from where it was paused.
- **Chain of Events:**
  1. **Pause Button Clicked**: `pause_button_callback` is triggered.
     - **Function**: `ButtonView.pause_button_callback`
     - Pauses the current playback and updates the `paused` state.
  2. **Resume Button Clicked**: `resume_button_callback` is triggered.
     - **Function**: `ButtonView.resume_button_callback`
     - Resumes playback from the paused state and updates the `paused` state.

### Skip the Current Track

- **Button:** ⏭️ Skip
- **Command:** `/skip`
- **Scenario:** A user skips the current track.
- **Expected Behavior:** The bot stops the current track and plays the next entry in the queue. If looping is enabled, the skipped track should move to the end of the queue.
- **Chain of Events:**
  1. **Skip Triggered**: `skip_button_callback` or `skip` command is triggered.
     - **Function**: `ButtonView.skip_button_callback`
     - **Function**: `MusicCommands.skip`
     - Stops the current playback.
  2. **Update Queue**:
     - If looping is enabled, the skipped track is moved to the end of the queue.
  3. **Play Next Track**:
     - **Function**: `play_next`
     - Retrieves the next entry from the queue and starts playback.
     - **Function**: `play_audio`

### Stop Playback

- **Button:** ⏹️ Stop
- **Command:** `/stop`
- **Scenario:** A user stops the playback.
- **Expected Behavior:** The bot stops the current track and disconnects from the voice channel. The queue playback is halted until a new play command is issued.
- **Chain of Events:**
  1. **Stop Triggered**: `stop_button_callback` or `stop` command is triggered.
     - **Function**: `ButtonView.stop_button_callback`
     - **Function**: `MusicCommands.stop`
     - Stops the current playback and disconnects from the voice channel.
  2. **Update Queue**:
     - The queue order remains unchanged, but playback is halted until a new play command is issued.

### Restart the Current Track

- **Button:** 🔄 Restart
- **Command:** `/restart`
- **Scenario:** A user restarts the current track.
- **Expected Behavior:** The bot stops the current track and starts playing it from the beginning.
- **Chain of Events:**
  1. **Restart Triggered**: `restart_button_callback` or `restart` command is triggered.
     - **Function**: `ButtonView.restart_button_callback`
     - **Function**: `MusicCommands.restart`
     - Stops the current playback.
  2. **Play Audio**:
     - **Function**: `play_audio`
     - Starts playing the current track from the beginning.

### Shuffle the Queue

- **Button:** 🔀 Shuffle
- **Command:** `/shuffle`
- **Scenario:** A user shuffles the queue.
- **Expected Behavior:** The bot shuffles the entries in the queue randomly. The current playing track should remain unaffected.
- **Chain of Events:**
  1. **Shuffle Triggered**: `shuffle_button_callback` or `shuffle` command is triggered.
     - **Function**: `ButtonView.shuffle_button_callback`
     - **Function**: `MusicCommands.shuffle`
     - Shuffles the queue entries.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Updates the queue and continues playing the current track.

### List the Queue

- **Button:** 📜 List Queue
- **Command:** `/list_queue`
- **Scenario:** A user requests the current queue.
- **Expected Behavior:** The bot sends a message with the current queue, listing all entries in order.
- **Chain of Events:**
  1. **List Queue Triggered**: `list_queue_button_callback` or `list_queue` command is triggered.
     - **Function**: `ButtonView.list_queue_button_callback`
     - **Function**: `MusicCommands.list_queue`
     - Retrieves the queue and sends a message with the queue details.

### Play the Next Track

- **Command:** `/play_next [title or URL or MP3 attachment]`
- **Scenario:** A user moves a specified track to the second position in the queue.
- **Expected Behavior:** The bot moves the specified track to the second position in the queue and plays it after the current track finishes.
- **Chain of Events:**
  1. **Play Next Triggered**: `play_next` command is triggered.
     - **Function**: `MusicCommands.play_next`
     - Processes the provided title, URL, or MP3 attachment.
  2. **Update Queue**:
     - **Function**: `BotQueue.add_to_queue`
     - Adds the new entry to the second position in the queue.
  3. **Check Playback State**:
     - If a track is currently playing, it continues playing.
     - The next track in the queue will be the specified one.

### Remove a Track by Title

- **Command:** `/remove_by_title [title]`
- **Scenario:** A user removes a specified track from the queue.
- **Expected Behavior:** The bot removes the specified track from the queue.
- **Chain of Events:**
  1. **Remove by Title Triggered**: `remove_by_title` command is triggered.
     - **Function**: `MusicCommands.remove_by_title`
     - Removes the specified track from the queue.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Updates the queue and continues playing the current track.

### Remove a Track by Index

- **Command:** `/remove_queue [index]`
- **Scenario:** A user removes a track from the queue by its index.
- **Expected Behavior:** The bot removes the specified track from the queue.
- **Chain of Events:**
  1. **Remove by Index Triggered**: `remove_queue` command is triggered.
     - **Function**: `MusicCommands.remove_queue`
     - Removes the specified track from the queue by its index.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Updates the queue and continues playing the current track.

### Play the Previous Track

- **Button:** ⏮️ Previous
- **Command:** `/previous`
- **Scenario:** A user plays the last entry that was being played.
- **Expected Behavior:** The bot stops the current track and plays the previous track.
- **Chain of Events:**
  1. **Previous Triggered**: `previous_button_callback` or `previous` command is triggered.
     - **Function**: `ButtonView.previous_button_callback`
     - **Function**: `MusicCommands.previous`
     - Stops the current playback.
  2. **Play Audio**:
     - **Function**: `play_audio`
     - Plays the last played track.

### Toggle Looping of the Current Track

- **Button:** 🔁 Loop
- **Scenario:** A user toggles the looping of the current track.
- **Expected Behavior:** The bot toggles the loop state for the current track. If enabled, the current track will repeat after it finishes playing.
- **Chain of Events:**
  1. **Loop Triggered**: `loop_button_callback` is triggered.
     - **Function**: `ButtonView.loop_button_callback`
     - Toggles the loop state and updates the button label.

### Favorite a Track

- **Button:** ⭐ Favorite / 💛 Favorited
- **Scenario:** A user favorites the current track.
- **Expected Behavior:** The bot updates the favorite status of the current track for the user.
- **Chain of Events:**
  1. **Favorite Triggered**: `favorite_button_callback` is triggered.
     - **Function**: `ButtonView.favorite_button_callback`
     - Updates the favorite status and updates the button label.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Saves the updated queue.

### Clear the Queue

- **Command:** `/clear_queue`
- **Scenario:** A user clears the queue except the currently playing entry.
- **Expected Behavior:** The bot clears all entries in the queue except the currently playing entry.
- **Chain of Events:**
  1. **Clear Queue Triggered**: `clear_queue` command is triggered.
     - **Function**: `MusicCommands.clear_queue`
     - Clears the queue, keeping only the currently playing entry.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Saves the updated queue.

### Search YouTube and Add to Queue

- **Command:** `/search_youtube [query]`
- **Scenario:** A user searches for a YouTube video and adds its audio to the queue.
- **Expected Behavior:** The bot searches YouTube for the query, retrieves the video info, and adds the audio to the queue.
- **Chain of Events:**
  1. **Search YouTube Triggered**: `search_youtube` command is triggered.
     - **Function**: `MusicCommands.search_youtube`
     - Searches YouTube for the query.
  2. **Fetch Video Info**:
     - **Function**: `fetch_info`
     - Retrieves the video info from YouTube.
  3. **Create Queue Entry**:
     - **Function**: `QueueEntry.__init__`
     - Creates a `QueueEntry` object with the video information.
  4. **Add to Queue**:
     - **Function**: `BotQueue.add_to_queue`
     - Adds the `QueueEntry` to the queue.
  5. **Check Playback State**:
     - If nothing is currently playing, it calls `play_audio` to start playback.
     - If the bot is already playing, the new entry is added to the end of the queue.
     - **Function**: `play_audio`

### Search and Play from Queue

- **Command:** `/search_and_play_from_queue [title]`
- **Scenario:** A user searches the current queue for a specific track and plays it.
- **Expected Behavior:** The bot searches the queue for the specified track, moves it to the top, and starts playing it.
- **Chain of Events:**
  1. **Search and Play Triggered**: `search_and_play_from_queue` command is triggered.
     - **Function**: `MusicCommands.search`
     - Searches the queue for the specified track.
  2. **Update Queue**:
     - **Function**: `BotQueue.add_to_queue`
     - Moves the specified track to the top of the queue.
  3. **Check Playback State**:
     - If a track is currently playing, it stops the playback.
  4. **Play Audio**:
     - **Function**: `play_audio`
     - Plays the specified track.

### Remove a Track

- **Button:** ❌ Remove
- **Scenario 1:** A user clicks Remove on a past song that is no longer playing, but another song is currently playing.
- **Expected Behavior:** The bot removes the specified past song from the queue without affecting the current playback.
- **Chain of Events:**

  1. **Remove Triggered**: `remove_button_callback` is triggered.
     - **Function**: `ButtonView.remove_button_callback`
     - Removes the specified past song from the queue.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Updates the queue and continues playing the current track.

- **Scenario 2:** A user clicks Remove on the song that is currently being played.
- **Expected Behavior:** The bot stops the current track, removes it from the queue, and plays the next entry in the queue.
- **Chain of Events:**
  1. **Remove Triggered**: `remove_button_callback` is triggered.
     - **Function**: `ButtonView.remove_button_callback`
     - Stops the current playback and removes the current track from the queue.
  2. **Play Next Track**:
     - **Function**: `play_next`
     - Retrieves the next entry from the queue and starts playback.
     - **Function**: `play_audio`

### Move Up

- **Button:** ⬆️ Move Up
- **Scenario:** A user clicks Move Up on a song that is not currently playing.
- **Expected Behavior:** The bot moves the specified song one position up in the queue without affecting the current playback.
- **Chain of Events:**
  1. **Move Up Triggered**: `move_up_button_callback` is triggered.
     - **Function**: `ButtonView.move_up_button_callback`
     - Identifies the specified song and its current position in the queue.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Moves the song one position up in the queue.
     - Continues playing the current track.

### Move Down

- **Button:** ⬇️ Move Down
- **Scenario:** A user clicks Move Down on a song that is not currently playing.
- **Expected Behavior:** The bot moves the specified song one position down in the queue without affecting the current playback.
- **Chain of Events:**
  1. **Move Down Triggered**: `move_down_button_callback` is triggered.
     - **Function**: `ButtonView.move_down_button_callback`
     - Identifies the specified song and its current position in the queue.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Moves the song one position down in the queue.
     - Continues playing the current track.

### Move to Top

- **Button:** ⬆️⬆️ Move to Top
- **Scenario:** A user clicks Move to Top on a song that is not currently playing.
- **Expected Behavior:** The bot moves the specified song to the top of the queue without affecting the current playback.
- **Chain of Events:**
  1. **Move to Top Triggered**: `move_to_top_button_callback` is triggered.
     - **Function**: `ButtonView.move_to_top_button_callback`
     - Identifies the specified song and its current position in the queue.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Moves the song to the top of the queue.
     - Continues playing the current track.

### Move to Bottom

- **Button:** ⬇️⬇️ Move to Bottom
- **Scenario:** A user clicks Move to Bottom on a song that is not currently playing.
- **Expected Behavior:** The bot moves the specified song to the bottom of the queue without affecting the current playback.
- **Chain of Events:**
  1. **Move to Bottom Triggered**: `move_to_bottom_button_callback` is triggered.
     - **Function**: `ButtonView.move_to_bottom_button_callback`
     - Identifies the specified song and its current position in the queue.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Moves the song to the bottom of the queue.
     - Continues playing the current track.

### Additional Scenario: Moving the Currently Playing Song

- **Scenario:** A user clicks Move Up/Down/To Top/To Bottom on the song that is currently being played.
- **Expected Behavior:** The bot does not change the position of the currently playing song immediately, but updates its position in the queue for the subsequent playbacks.
- **Chain of Events:**
  1. **Move Triggered**: `move_up_button_callback`/`move_down_button_callback`/`move_to_top_button_callback`/`move_to_bottom_button_callback` is triggered.
     - **Function**: `ButtonView.move_up_button_callback`/`move_down_button_callback`/`move_to_top_button_callback`/`move_to_bottom_button_callback`
     - Identifies the currently playing song and its current position in the queue.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Updates the position of the currently playing song in the queue for subsequent playbacks.
     - Continues playing the current track until it ends.

### MP3 List

- **Command:** `.mp3_list [URL or attachments]`
- **Scenario:** A user provides a YouTube URL or attaches multiple MP3 files.
- **Expected Behavior:** The bot connects to the user's voice channel, adds the provided MP3 files or YouTube video entries to the queue, and starts playing the first added entry if nothing is currently playing. If the queue is already playing, the new entries will be added to the end of the queue.
- **Chain of Events:**
  1. **MP3 List Command Triggered**: `.mp3_list` command is triggered.
     - **Function**: `MusicCommands.mp3_list`
     - Checks if the voice client is connected or connects if necessary.
  2. **Process Attachments**:
     - **Function**: `download_file`
     - **Function**: `QueueEntry.__init__`
     - Downloads each MP3 file and creates `QueueEntry` objects.
  3. **Add to Queue**:
     - **Function**: `BotQueue.add_to_queue`
     - Adds the `QueueEntry` objects to the queue.
  4. **Fetch Video Info**:
     - **Function**: `fetch_info`
     - Retrieves the video info from YouTube if a URL is provided.
  5. **Check Playback State**:
     - If the bot is not already playing, it calls `play_audio` to start playback of the first added entry.
     - If the bot is already playing, the new entries are added to the end of the queue.
     - **Function**: `play_audio`

### Search and Add to Queue from YouTube

- **Command:** `/search_youtube [query]`
- **Scenario:** A user searches for a YouTube video and adds its audio to the queue.
- **Expected Behavior:** The bot searches YouTube for the query, retrieves the video info, and adds the audio to the queue.
- **Chain of Events:**
  1. **Search YouTube Triggered**: `search_youtube` command is triggered.
     - **Function**: `MusicCommands.search_youtube`
     - Searches YouTube for the query.
  2. **Fetch Video Info**:
     - **Function**: `fetch_info`
     - Retrieves the video info from YouTube.
  3. **Create Queue Entry**:
     - **Function**: `QueueEntry.__init__`
     - Creates a `QueueEntry` object with the video information.
  4. **Add to Queue**:
     - **Function**: `BotQueue.add_to_queue`
     - Adds the `QueueEntry` to the queue.
  5. **Check Playback State**:
     - If nothing is currently playing, it calls `play_audio` to start playback.
     - If the bot is already playing, the new entry is added to the end of the queue.
     - **Function**: `play_audio`

### Search and Play from Queue

- **Command:** `/search_and_play_from_queue [title]`
- **Scenario:** A user searches the current queue for a specific track and plays it.
- **Expected Behavior:** The bot searches the queue for the specified track, moves it to the top, and starts playing it.
- **Chain of Events:**
  1. **Search and Play Triggered**: `search_and_play_from_queue` command is triggered.
     - **Function**: `MusicCommands.search`
     - Searches the queue for the specified track.
  2. **Update Queue**:
     - **Function**: `BotQueue.add_to_queue`
     - Moves the specified track to the top of the queue.
  3. **Check Playback State**:
     - If a track is currently playing, it stops the playback.
  4. **Play Audio**:
     - **Function**: `play_audio`
     - Plays the specified track.

### Clear the Queue

- **Command:** `/clear_queue`
- **Scenario:** A user clears the queue except the currently playing entry.
- **Expected Behavior:** The bot clears all entries in the queue except the currently playing entry.
- **Chain of Events:**
  1. **Clear Queue Triggered**: `clear_queue` command is triggered.
     - **Function**: `MusicCommands.clear_queue`
     - Clears the queue, keeping only the currently playing entry.
  2. **Update Queue**:
     - **Function**: `BotQueue.save_queues`
     - Saves the updated queue.
