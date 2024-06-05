## Use Cases

### Play a Single Video or MP3 File

- **Command:** `/play [URL or attachment]`
- **Scenario:** A user provides a YouTube URL or attaches an MP3 file.
- **Expected Behavior:** The bot connects to the user's voice channel, adds the entry to the queue, and starts playing the audio. If the queue was empty, it will start playing the added entry immediately. If there are already entries in the queue, the new entry will be added to the end of the queue.
- **Chain of Events:**
  1. `play` command is triggered.
  2. `process_single_video_or_mp3` or `process_play_command` is called.
  3. `fetch_info` retrieves the video info.
  4. `QueueEntry` is created and added to the queue using `queue_manager.add_to_queue`.
  5. If the bot is not already playing:
     - `play_audio` is called to start playback.
  6. If the bot is already playing:
     - The new entry is added to the end of the queue, and playback of the current entry continues.

### Play a Playlist

- **Command:** `/play [playlist URL]`
- **Scenario:** A user provides a YouTube playlist URL.
- **Expected Behavior:** The bot connects to the user's voice channel, adds all videos in the playlist to the queue, and starts playing the first video. Subsequent videos in the playlist will play automatically after the current one finishes.
- **Chain of Events:**
  1. `play` command is triggered.
  2. `process_play_command` handles the playlist URL.
  3. `fetch_playlist_length` and `fetch_info` retrieve playlist info.
  4. Multiple `QueueEntry` instances are created and added to the queue.
  5. If the bot is not already playing:
     - `play_audio` is called to start playback of the first video.
  6. If the bot is already playing:
     - The playlist entries are added to the end of the queue, and playback of the current entry continues.

### Pause and Resume Playback

- **Button:** ⏸️ Pause / ▶️ Resume
- **Scenario:** A user pauses and then resumes the playback.
- **Expected Behavior:** The bot pauses the current track and resumes playback when the resume button is clicked. The playback should continue from where it was paused.
- **Chain of Events:**
  1. `pause_button_callback` is triggered.
  2. The bot pauses the current playback and updates the `paused` state.
  3. `resume_button_callback` is triggered.
  4. The bot resumes playback from the paused state and updates the `paused` state.

### Skip the Current Track

- **Button:** ⏭️ Skip
- **Command:** `/skip`
- **Scenario:** A user skips the current track.
- **Expected Behavior:** The bot stops the current track and plays the next entry in the queue. If looping is enabled, the skipped track should move to the end of the queue.
- **Chain of Events:**
  1. `skip_button_callback` or `skip` command is triggered.
  2. The bot stops the current playback.
  3. If looping is enabled, the skipped track is moved to the end of the queue.
  4. `play_next` is called to play the next entry in the queue.
  5. The bot retrieves the next entry from the queue and starts playback.
  6. The currently playing entry is updated in the queue manager.

### Stop Playback

- **Button:** ⏹️ Stop
- **Command:** `/stop`
- **Scenario:** A user stops the playback.
- **Expected Behavior:** The bot stops the current track and disconnects from the voice channel. The queue playback is halted until a new play command is issued. The currently played song moves to the end of the queue.
- **Chain of Events:**
  1. `stop_button_callback` or `stop` command is triggered.
  2. The bot stops the current playback.
  3. The stopped track is moved to the end of the queue.
  4. The bot disconnects from the voice channel.
  5. The queue manager's `stop_is_triggered` state is set to `True`.
  6. The queue order remains unchanged except for the moved track, but playback is halted until a new play command is issued.

### Restart the Current Track

- **Button:** 🔄 Restart
- **Command:** `/restart`
- **Scenario:** A user restarts the current track.
- **Expected Behavior:** The bot stops the current track and starts playing it from the beginning.
- **Chain of Events:**
  1. `restart_button_callback` or `restart` command is triggered.
  2. The bot stops the current playback.
  3. `play_audio` is called to restart the current track.

### Shuffle the Queue

- **Button:** 🔀 Shuffle
- **Command:** `/shuffle`
- **Scenario:** A user shuffles the queue.
- **Expected Behavior:** The bot shuffles the entries in the queue randomly. The current playing track should remain unaffected.
- **Chain of Events:**
  1. `shuffle_button_callback` or `shuffle` command is triggered.
  2. The queue entries are shuffled.
  3. The bot updates the queue and continues playing the current track.

### List the Queue

- **Button:** 📜 List Queue
- **Command:** `/list_queue`
- **Scenario:** A user requests the current queue.
- **Expected Behavior:** The bot sends a message with the current queue, listing all entries in order.
- **Chain of Events:**
  1. `list_queue_button_callback` or `list_queue` command is triggered.
  2. The bot retrieves the queue and sends a message with the queue details.

### Play the Next Track

- **Command:** `/play_next [title or URL or MP3 attachment]`
- **Scenario:** A user moves a specified track to the second position in the queue.
- **Expected Behavior:** The bot moves the specified track to the second position in the queue and plays it after the current track finishes.
- **Chain of Events:**
  1. `play_next` command is triggered.
  2. If a YouTube playlist URL is provided:
     - `process_play_command` handles the playlist URL.
     - `fetch_playlist_length` and `fetch_info` retrieve playlist info.
     - Multiple `QueueEntry` instances are created and added to the queue at the second position.
  3. If an MP3 file is provided:
     - `download_file` is called to download the MP3 file.
     - `QueueEntry` is created and added to the queue at the second position.
  4. If a title is provided:
     - The specified track is moved to the second position in the queue.
  5. The bot continues playing the current track, and the next track in the queue will be the specified one.

### Remove a Track by Title

- **Command:** `/remove_by_title [title]`
- **Scenario:** A user removes a specified track from the queue.
- **Expected Behavior:** The bot removes the specified track from the queue.
- **Chain of Events:**
  1. `remove_by_title` command is triggered.
  2. The specified track is removed from the queue.
  3. The bot updates the queue and continues playing the current track.

### Remove a Track by Index

- **Command:** `/remove_queue [index]`
- **Scenario:** A user removes a track from the queue by its index.
- **Expected Behavior:** The bot removes the specified track from the queue.
- **Chain of Events:**
  1. `remove_queue` command is triggered.
  2. The specified track is removed from the queue by its index.
  3. The bot updates the queue and continues playing the current track.

### Play the Previous Track

- **Button:** ⏮️ Previous
- **Command:** `/previous`
- **Scenario:** A user plays the last entry that was being played.
- **Expected Behavior:** The bot stops the current track and plays the previous track.
- **Chain of Events:**
  1. `previous_button_callback` or `previous` command is triggered.
  2. The bot stops the current playback.
  3. The bot plays the last played track.

### Toggle Looping of the Current Track

- **Button:** 🔁 Loop
- **Scenario:** A user toggles the looping of the current track.
- **Expected Behavior:** The bot toggles the loop state for the current track. If enabled, the current track will repeat after it finishes playing.
- **Chain of Events:**
  1. `loop_button_callback` is triggered.
  2. The bot toggles the loop state and updates the button label.

### Favorite a Track

- **Button:** ⭐ Favorite / 💛 Favorited
- **Scenario:** A user favorites the current track.
- **Expected Behavior:** The bot updates the favorite status of the current track for the user.
- **Chain of Events:**
  1. `favorite_button_callback` is triggered.
  2. The bot updates the favorite status and updates the button label.

### Clear the Queue

- **Command:** `/clear_queue`
- **Scenario:** A user clears the queue except the currently playing entry.
- **Expected Behavior:** The bot clears all entries in the queue except the currently playing entry.
- **Chain of Events:**
  1. `clear_queue` command is triggered.
  2. The bot clears the queue, keeping only the currently playing entry.

### Search YouTube and Add to Queue

- **Command:** `/search_youtube [query]`
- **Scenario:** A user searches for a YouTube video and adds its audio to the queue.
- **Expected Behavior:** The bot searches YouTube for the query, retrieves the video info, and adds the audio to the queue.
- **Chain of Events:**
  1. `search_youtube` command is triggered.
  2. The bot searches YouTube and retrieves the video info.
  3. A `QueueEntry` is created and added to the queue.
  4. If nothing is currently playing:
     - `play_audio` is called to start playback.
  5. If the bot is already playing:
     - The new entry is added to the end of the queue, and playback of the current entry continues.

### Search and Play from Queue

- **Command:** `/search_and_play_from_queue [title]`
- **Scenario:** A user searches the current queue for a specific track and plays it.
- **Expected Behavior:** The bot searches the queue for the specified track, moves it to the top, and starts playing it.
- **Chain of Events:**
  1. `search_and_play_from_queue` command is triggered.
  2. The bot searches the queue and moves the specified track to the top.
  3. If a track is currently playing, it stops the playback.
  4. `play_audio` is called to play the specified track.

### Remove a Track

- **Button:** ❌ Remove
- **Scenario 1:** A user clicks Remove on a past song that is no longer playing, but another song is currently playing.
- **Expected Behavior:** The bot removes the specified past song from the queue without affecting the current playback.
- **Chain of Events:**

  1. `remove_button_callback` is triggered.
  2. The bot removes the specified past song from the queue.
  3. The bot updates the queue and continues playing the current track.

- **Scenario 2:** A user clicks Remove on the song that is currently being played.
- **Expected Behavior:** The bot stops the current track, removes it from the queue, and plays the next entry in the queue.
- **Chain of Events:**
  1. `remove_button_callback` is triggered.
  2. The bot stops the current playback.
  3. The bot removes the current track from the queue.
  4. `play_next` is called to play the next entry in the queue.
  5. The bot retrieves the next entry from the queue and starts playback.

### Move Up

- **Button:** ⬆️ Move Up
- **Scenario:** A user clicks Move Up on a song that is not currently playing.
- **Expected Behavior:** The bot moves the specified song one position up in the queue without affecting the current playback.
- **Chain of Events:**
  1. `move_up_button_callback` is triggered.
  2. The bot identifies the specified song and its current position in the queue.
  3. The bot moves the song one position up in the queue.
  4. The bot updates the queue.
  5. The bot continues playing the current track.
  6. When the current song ends, the next song in the updated queue order is played.

### Move Down

- **Button:** ⬇️ Move Down
- **Scenario:** A user clicks Move Down on a song that is not currently playing.
- **Expected Behavior:** The bot moves the specified song one position down in the queue without affecting the current playback.
- **Chain of Events:**
  1. `move_down_button_callback` is triggered.
  2. The bot identifies the specified song and its current position in the queue.
  3. The bot moves the song one position down in the queue.
  4. The bot updates the queue.
  5. The bot continues playing the current track.
  6. When the current song ends, the next song in the updated queue order is played.

### Move to Top

- **Button:** ⬆️⬆️ Move to Top
- **Scenario:** A user clicks Move to Top on a song that is not currently playing.
- **Expected Behavior:** The bot moves the specified song to the top of the queue without affecting the current playback.
- **Chain of Events:**
  1. `move_to_top_button_callback` is triggered.
  2. The bot identifies the specified song and its current position in the queue.
  3. The bot moves the song to the top of the queue.
  4. The bot updates the queue.
  5. The bot continues playing the current track.
  6. When the current song ends, the song at the top of the queue (the moved song) is played next.

### Move to Bottom

- **Button:** ⬇️⬇️ Move to Bottom
- **Scenario:** A user clicks Move to Bottom on a song that is not currently playing.
- **Expected Behavior:** The bot moves the specified song to the bottom of the queue without affecting the current playback.
- **Chain of Events:**
  1. `move_to_bottom_button_callback` is triggered.
  2. The bot identifies the specified song and its current position in the queue.
  3. The bot moves the song to the bottom of the queue.
  4. The bot updates the queue.
  5. The bot continues playing the current track.
  6. When the current song ends, the next song in the updated queue order is played, continuing from the top.

### Additional Scenario: Moving the Currently Playing Song

- **Scenario:** A user clicks Move Up/Down/To Top/To Bottom on the song that is currently being played.
- **Expected Behavior:** The bot does not change the position of the currently playing song immediately, but updates its position in the queue for the subsequent playbacks.
- **Chain of Events:**
  1. `move_up_button_callback`/`move_down_button_callback`/`move_to_top_button_callback`/`move_to_bottom_button_callback` is triggered.
  2. The bot identifies the currently playing song and its current position in the queue.
  3. The bot updates the position of the currently playing song in the queue for subsequent playbacks.
  4. The bot continues playing the current track until it ends.
  5. When the current song ends, the bot plays the next song in the updated queue order.

### MP3 List

- **Command:** `.mp3_list [URL or attachments]`
- **Scenario:** A user provides a YouTube URL or attaches multiple MP3 files.
- **Expected Behavior:** The bot connects to the user's voice channel, adds the provided MP3 files or YouTube video entries to the queue, and starts playing the first added entry if nothing is currently playing. If the queue is already playing, the new entries will be added to the end of the queue.
- **Chain of Events:**
  1. `.mp3_list` command is triggered.
  2. The bot checks if there are MP3 attachments in the message.
  3. For each MP3 file:
     1. `download_file` is called to download the MP3 file.
     2. A `QueueEntry` is created for each MP3 file and added to the queue using `queue_manager.add_to_queue`.
  4. If a YouTube URL is provided:
     1. `fetch_info` retrieves the video info.
     2. `QueueEntry` is created and added to the queue using `queue_manager.add_to_queue`.
  5. If the bot is not already playing:
     - `play_audio` is called to start playback of the first added entry.
  6. If the bot is already playing:
     - The new entries are added to the end of the queue, and playback of the current entry continues.
