
# TODO: Off-Brand Pandora Mode for Discord Radio Bot

## Feature Goal:
Implement a new slash command `/off_brand_pandora` that allows a user to:
- Choose a "mood" and genre(s) to start an auto-playing music session.
- OR use the currently playing song to discover and queue similar music.
- Continuously play related music until the user explicitly stops it.

---

## Implementation Steps

### ✅ Step 1: Add Slash Command
- [ ] Define a new slash command `/off_brand_pandora` in `commands.py`.
- [ ] Accept parameters: mood (optional), genre(s) (optional).
- [ ] Detect if a song is currently playing to optionally seed from that.

### ✅ Step 2: Get Song Info (if available)
- [ ] Use current queue or `now_playing_helper.py` to extract artist/title.
- [ ] Normalize and sanitize song metadata for API use.

### ✅ Step 3: MusicBrainz Integration
- [ ] Use `musicbrainzngs` or raw HTTP to:
  - [ ] Search for artist based on current or selected genre.
  - [ ] Retrieve similar artists via artist-rels.
  - [ ] Retrieve top songs from those artists.
- [ ] (Optional) Use AcousticBrainz for mood/genre filtering.

### ✅ Step 4: Queue Background Playback
- [ ] Create a loop task to search and queue YouTube links using `yt_dlp`.
- [ ] Leverage existing `queue_manager` and playback logic.
- [ ] Ensure songs queue one by one as each track ends.

### ✅ Step 5: Control & Stop Logic
- [ ] Monitor if user pauses, stops, or kills the bot.
- [ ] Cancel the background task on stop.
- [ ] Add flag to prevent multiple sessions running simultaneously.

---

## Optional Enhancements
- [ ] Add interactive buttons to skip or fine-tune recommendations.
- [ ] Persist session state in a file or cache in case of restart.
- [ ] Use Discord embeds to show current "radio session" metadata.

---

## Files Affected
- `commands.py`
- `command_functions.py`
- `now_playing_helper.py`
- `playback.py`
- `queue_manager.py`
