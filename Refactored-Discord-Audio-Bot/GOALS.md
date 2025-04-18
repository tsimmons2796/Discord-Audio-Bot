# Goals

## Overview

This document defines the project goals based on the provided use-case scenarios. Each goal describes the desired behavior of the system along with detailed acceptance criteria. An automated AI workflow can use these goals to compare the current project’s behavior with the expected chain-of-events, identifying discrepancies or areas needing refactoring.

> **Note:** The automated workflow should verify that each goal is met by checking logs, state changes (such as the queue state and playback status), and other side effects defined in the chain-of-events.

---

## 1. Single Video/MP3 Playback

**Objective:**  
When a user issues the `/play` command with a YouTube URL or an MP3 attachment, the bot must play that single entry.

**Expected Behavior:**

- **Voice Connection:**
  - Check if the bot is connected to the user's voice channel; if not, connect.
- **Processing Command:**
  - Execute the `play` command (via `MusicCommands.play`) and process the request.
- **Fetching Media Info:**
  - Call `fetch_info` (and/or `process_single_video_or_mp3`) to retrieve video or MP3 metadata.
- **Queue Management:**
  - Create a `QueueEntry` instance using `QueueEntry.__init__`.
  - Add the entry to the queue using `BotQueue.add_to_queue`.
- **Playback Initiation:**
  - If the queue was empty, start playback immediately via `play_audio`; if not, append the new entry.

**Acceptance Criteria:**

- The bot establishes a voice connection if not already connected.
- The media information is correctly fetched and stored.
- A queue entry is created and the queue state is updated.
- Playback starts immediately if appropriate, or the entry is appended if already playing.

---

## 2. Playlist Playback

**Objective:**  
Upon receiving a YouTube playlist URL via `/play`, the bot should queue all playlist videos and begin playback from the first.

**Expected Behavior:**

- **Voice Connection & Command Processing:**
  - Similar to single playback, ensure a voice connection.
  - Trigger the `play` command and process via `MusicCommands.play`.
- **Fetching Playlist Info:**
  - Retrieve playlist details using `fetch_info` and `fetch_playlist_length`.
- **Queue Management:**
  - Create multiple `QueueEntry` objects (one per video).
  - Add each entry to the queue with `BotQueue.add_to_queue`.
- **Playback Initiation:**
  - Start playing the first video immediately if no playback is in progress.
  - Subsequent videos will play automatically in order.

**Acceptance Criteria:**

- The playlist info (including length) is successfully retrieved.
- All videos are correctly represented as individual queue entries.
- The queue reflects the correct order and count.
- Playback of the first video starts, and subsequent videos follow automatically.

---

## 3. Pause and Resume Playback

**Objective:**  
Allow users to pause and resume the current playback using UI buttons.

**Expected Behavior:**

- **Pause Action:**
  - On pause button click, trigger `pause_button_callback` (from `ButtonView`), which pauses the current track and updates the paused state.
- **Resume Action:**
  - On resume button click, trigger `resume_button_callback` (from `ButtonView`), resuming playback from where it was paused.

**Acceptance Criteria:**

- The playback pauses immediately when the pause button is activated.
- Resuming playback picks up exactly where it left off.
- The UI state (button labels) reflects the correct action (paused/resumed).

---

## 4. Skip the Current Track

**Objective:**  
Enable users to skip the current track either via a button or `/skip` command.

**Expected Behavior:**

- **Skip Command Execution:**
  - Trigger either `skip_button_callback` or `MusicCommands.skip`.
- **Queue Update:**
  - If looping is enabled, move the skipped track to the end of the queue.
- **Playback Transition:**
  - Stop the current playback and immediately start playing the next track using `play_next` and `play_audio`.

**Acceptance Criteria:**

- The current track stops and the next track starts.
- If looping is active, the skipped track is repositioned to the end of the queue.
- The queue state reflects the correct ordering after the skip.

---

## 5. Stop Playback

**Objective:**  
Allow users to stop playback and disconnect the bot from the voice channel via `/stop` or a stop button.

**Expected Behavior:**

- **Stop Execution:**
  - Trigger either `stop_button_callback` or `MusicCommands.stop`.
- **Voice Disconnection:**
  - Stop the current track and disconnect from the voice channel.
- **Queue Behavior:**
  - Playback halts; the queue remains unchanged but inactive until a new play command is issued.

**Acceptance Criteria:**

- Playback halts immediately.
- The bot disconnects from the voice channel.
- The queue is preserved (order unchanged) but remains inactive until restarted.

---

## 6. Restart the Current Track

**Objective:**  
Enable restarting the current track from the beginning using `/restart` or a restart button.

**Expected Behavior:**

- **Restart Action:**
  - Trigger `restart_button_callback` or `MusicCommands.restart`.
- **Playback Reinitialization:**
  - Stop the current track and reinitialize it from the beginning via `play_audio`.

**Acceptance Criteria:**

- The current track stops and restarts from time zero.
- The playback state is refreshed, and the UI (if applicable) reflects the restart action.

---

## 7. Shuffle the Queue

**Objective:**  
Implement functionality to shuffle the queue while leaving the currently playing track unaffected.

**Expected Behavior:**

- **Shuffle Command:**
  - Trigger `shuffle_button_callback` or `/shuffle`.
- **Queue Update:**
  - Randomly reorder the queue entries using `MusicCommands.shuffle` and save the updated order with `BotQueue.save_queues`.
- **Playback Integrity:**
  - The current track continues playing without interruption.

**Acceptance Criteria:**

- The order of queued tracks is randomized (except the current track).
- The current playback remains uninterrupted.
- Verification via queue inspection shows a new random order.

---

## 8. List the Queue

**Objective:**  
Allow users to view the current queue through the `/list_queue` command or list queue button.

**Expected Behavior:**

- **List Command:**
  - Trigger `list_queue_button_callback` or `MusicCommands.list_queue`.
- **Display:**
  - Retrieve and display all queue entries in order.

**Acceptance Criteria:**

- The output accurately lists every entry in the current queue.
- The order matches the internal queue state.
- The display is clear and user-friendly.

---

## 9. Play Next Track Insertion

**Objective:**  
Allow users to insert a track to play immediately after the current one using `/play_next`.

**Expected Behavior:**

- **Insertion Command:**
  - Process the `/play_next` command via `MusicCommands.play_next`.
- **Queue Update:**
  - Insert the specified track at the second position in the queue using `BotQueue.add_to_queue`.
- **Playback Continuity:**
  - If a track is already playing, continue playback; the inserted track will be the next one played.

**Acceptance Criteria:**

- The specified track is correctly positioned as the second entry.
- The current track is not interrupted.
- Playback moves to the inserted track once the current track ends.

---

## 10. Remove a Track by Title

**Objective:**  
Allow removal of a track from the queue by providing its title using `/remove_by_title`.

**Expected Behavior:**

- **Remove Command:**
  - Trigger `MusicCommands.remove_by_title` with the given title.
- **Queue Update:**
  - Remove the matching track from the queue and update the state via `BotQueue.save_queues`.

**Acceptance Criteria:**

- The track with the specified title is removed from the queue.
- The updated queue is correctly persisted.
- Playback of other tracks remains unaffected.

---

## 11. Remove a Track by Index

**Objective:**  
Allow removal of a track based on its index in the queue using `/remove_queue`.

**Expected Behavior:**

- **Remove Command:**
  - Trigger `MusicCommands.remove_queue` with the provided index.
- **Queue Update:**
  - Remove the track at that index and update the queue using `BotQueue.save_queues`.

**Acceptance Criteria:**

- The track at the specified index is removed.
- The new queue order is verified.
- There is no disruption to the current playback (unless the removed track was playing).

---

## 12. Play the Previous Track

**Objective:**  
Allow users to go back to the last played track using `/previous` or a previous button.

**Expected Behavior:**

- **Previous Command:**
  - Trigger `previous_button_callback` or `MusicCommands.previous`.
- **Playback Update:**
  - Stop current playback.
  - Retrieve the last played track and restart playback via `play_audio`.

**Acceptance Criteria:**

- The previous track is correctly identified and played.
- Current playback stops immediately upon command execution.
- The UI/state reflects the change to the previous track.

---

## 13. Toggle Looping of the Current Track

**Objective:**  
Allow users to toggle looping for the current track with a loop button.

**Expected Behavior:**

- **Loop Toggle:**
  - Trigger `loop_button_callback` (from `ButtonView`).
  - Update the loop state so that when enabled, the current track repeats after finishing.
- **UI Update:**
  - Adjust button labels or indicators to reflect the looping state.

**Acceptance Criteria:**

- The loop state is correctly toggled on or off.
- When looping is enabled, the current track repeats seamlessly.
- The UI displays the correct loop state.

---

## 14. Favorite a Track

**Objective:**  
Allow users to mark a track as a favorite via the favorite button.

**Expected Behavior:**

- **Favorite Action:**
  - Trigger `favorite_button_callback` (from `ButtonView`).
- **Status Update:**
  - Update the favorite status of the current track and save changes using `BotQueue.save_queues`.
- **UI Feedback:**
  - Change the button label (e.g., from ⭐ Favorite to 💛 Favorited).

**Acceptance Criteria:**

- The favorite status is toggled correctly.
- Changes are persisted in the queue.
- The UI reflects the change immediately.

---

## 15. Clear the Queue

**Objective:**  
Allow users to clear all queue entries except the currently playing track via `/clear_queue`.

**Expected Behavior:**

- **Clear Command:**
  - Trigger `MusicCommands.clear_queue`.
- **Queue Update:**
  - Remove all entries except the one currently playing.
  - Save the updated queue using `BotQueue.save_queues`.

**Acceptance Criteria:**

- The queue is emptied correctly while keeping the current track.
- The updated queue state is accurately persisted.
- Subsequent commands work on the reduced queue.

---

## 16. MP3 List Playback

**Objective:**  
Handle multiple MP3 files or YouTube URLs provided as attachments via the `.mp3_list` command.

**Expected Behavior:**

- **Command Processing:**
  - Trigger `.mp3_list` and ensure a voice connection.
- **Media Processing:**
  - Process each attachment using `download_file` and create corresponding `QueueEntry` objects.
  - For URLs, use `fetch_info` to retrieve video data.
- **Queue Management & Playback:**
  - Add each entry to the queue via `BotQueue.add_to_queue`.
  - If no track is playing, initiate playback with `play_audio`; otherwise, append to the queue.

**Acceptance Criteria:**

- Each MP3 file or URL is processed correctly.
- All entries are queued in the correct order.
- Playback starts appropriately based on queue state.

---

## 17. Search YouTube and Add to Queue

**Objective:**  
Allow users to search for a YouTube video using `/search_youtube` and add the result to the queue.

**Expected Behavior:**

- **Search Execution:**
  - Trigger `search_youtube` and execute `MusicCommands.search_youtube`.
- **Information Retrieval:**
  - Fetch video info using `fetch_info`.
- **Queue Update & Playback:**
  - Create a `QueueEntry` and add it to the queue.
  - Initiate playback if no track is currently playing, or append otherwise.

**Acceptance Criteria:**

- The search query returns correct video information.
- The new queue entry reflects the searched video.
- Playback status is consistent with the queue’s state.

---

## 18. Search and Play from Queue

**Objective:**  
Enable users to search the current queue for a track and bring it to the top using `/search_and_play_from_queue`.

**Expected Behavior:**

- **Search Action:**
  - Trigger `search_and_play_from_queue` via `MusicCommands.search`.
- **Queue Reordering:**
  - Locate the track and reposition it at the top using `BotQueue.add_to_queue`.
- **Playback Update:**
  - If necessary, stop the current playback and start the selected track using `play_audio`.

**Acceptance Criteria:**

- The specified track is correctly identified in the queue.
- The track is moved to the top, and playback reflects this change.
- There is no disruption if the track is already in a suitable position.

---

## 19. Remove a Track via Button

**Objective:**  
Allow users to remove a track via a UI remove button, handling both non-current and current tracks.

**Expected Behavior:**

- **Remove Action for Non-current Track:**
  - Trigger `remove_button_callback` to remove the past (already played) track.
  - Update the queue via `BotQueue.save_queues`.
- **Remove Action for Current Track:**
  - Trigger `remove_button_callback`, which stops the current track.
  - Remove it from the queue and immediately trigger `play_next`/`play_audio` to play the next track.

**Acceptance Criteria:**

- The track is removed correctly from the queue.
- For current track removal, playback transitions smoothly to the next track.
- The queue state is accurately updated and saved.

---

## 20. Move Track Up

**Objective:**  
Allow users to move a track up one position in the queue using the Move Up button.

**Expected Behavior:**

- **Move Up Action:**
  - Trigger `move_up_button_callback` from `ButtonView`.
- **Queue Update:**
  - Identify the target track and shift it one position upward.
  - Save the updated order using `BotQueue.save_queues`.
- **Playback Impact:**
  - The current track remains unaffected.

**Acceptance Criteria:**

- The target track’s position is incremented correctly.
- The queue order reflects the move.
- Playback continues uninterrupted.

---

## 21. Move Track Down

**Objective:**  
Allow users to move a track down one position in the queue using the Move Down button.

**Expected Behavior:**

- **Move Down Action:**
  - Trigger `move_down_button_callback` from `ButtonView`.
- **Queue Update:**
  - Identify the target track and shift it one position downward.
  - Persist the new order using `BotQueue.save_queues`.
- **Playback Impact:**
  - Ensure that the current track is not affected by this change.

**Acceptance Criteria:**

- The queue order is updated to reflect the move.
- The operation does not disturb the current playback.

---

## 22. Move Track to Top

**Objective:**  
Enable users to move a track to the very top of the queue using the Move to Top button.

**Expected Behavior:**

- **Move to Top Action:**
  - Trigger `move_to_top_button_callback` from `ButtonView`.
- **Queue Update:**
  - Identify the target track and reposition it at the beginning of the queue.
  - Save the updated queue order using `BotQueue.save_queues`.
- **Playback Impact:**
  - The currently playing track continues until finished.

**Acceptance Criteria:**

- The track is repositioned at the top.
- Queue order is correctly persisted.
- There is no immediate interruption of the current playback.

---

## 23. Move Track to Bottom

**Objective:**  
Enable users to move a track to the bottom of the queue using the Move to Bottom button.

**Expected Behavior:**

- **Move to Bottom Action:**
  - Trigger `move_to_bottom_button_callback` from `ButtonView`.
- **Queue Update:**
  - Identify the target track and move it to the end of the queue.
  - Persist the new ordering with `BotQueue.save_queues`.
- **Playback Impact:**
  - The current playback continues unaffected.

**Acceptance Criteria:**

- The track is correctly repositioned at the bottom.
- Queue integrity is maintained.
- Playback remains uninterrupted.

---

## 24. Moving the Currently Playing Track

**Objective:**  
When a user attempts to move the currently playing track, the bot should update its future position without interrupting current playback.

**Expected Behavior:**

- **Move Action:**
  - Trigger one of the move callbacks (`move_up_button_callback`, `move_down_button_callback`, `move_to_top_button_callback`, or `move_to_bottom_button_callback`).
- **Queue Update:**
  - Identify the currently playing track and update its position in the queue for subsequent rounds.
- **Playback Impact:**
  - The currently playing track continues until it ends; the new order will be applied next.

**Acceptance Criteria:**

- The currently playing track is not interrupted immediately.
- Its new position is recorded and will take effect in future playback rounds.
- The updated queue reflects this change correctly.

---

## Conclusion

This document specifies the granular goals for each use-case. The automated AI workflow can use the acceptance criteria to perform checks, validate logs, inspect state changes, and confirm that the system behaves as expected. Any discrepancy between the current behavior and these goals will pinpoint where fixes or refactoring are necessary.
