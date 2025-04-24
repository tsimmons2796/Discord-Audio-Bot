🎟️ Story Ticket: Enhance Pandora-style Discovery with Spotify API Integration
Summary: We want to improve the discover command by using Spotify's rich music metadata and recommendations engine. The current implementation uses Last.fm to get similar artists and tag-based results. The goal is to replace or augment this with Spotify to offer a more intelligent, relevant, and customizable music discovery experience.

⚖️ Legal Considerations for Spotify API Usage
To stay on the safe side when using the Spotify API for discovery functionality in your bot:

Personal Use Only (if not licensed):

Spotify's Developer Terms of Service state that apps must not be commercial unless you have a commercial agreement.

Do not cache or store full track previews or any protected content long-term.

You're allowed to use track metadata (artist name, track name, etc.) and only for discovery/search—not playback from Spotify.

No Spotify Playback Without SDK Agreement:

Do not use Spotify audio playback APIs unless the user is authenticated and you're using their official SDK (Web Playback SDK or iOS/Android SDK).

Your bot cannot play Spotify tracks directly. You're good as long as you're just discovering tracks/artists and sending those to a YouTube search or similar.

Rate Limits & API Fair Use:

Respect rate limits (usually 600 requests per 60 minutes for most endpoints).

Do not make excessive API calls in a short time span (e.g., bulk artist lookups on every button click).

Privacy:

If you request user tokens for personalized Spotify data, you must have a privacy policy and secure data handling.

✅ Acceptance Criteria:
User can invoke /discover with the same base functionality (mood, genre).

Spotify is used to search for a seed track or seed artist (from currently playing or tags).

Spotify recommendation endpoint is used to find new songs.

The results are searched on YouTube and queued using the existing logic.

Supports "Surprise me" mode if no seed or tags are specified.

Provides ephemeral confirmation message listing mood, genre, seed artist, and count of queued results.

🔧 Implementation Tasks:
🔐 API & Authentication
Register a Spotify Developer app at https://developer.spotify.com.

Store SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env.

Add logic in config.py to expose Spotify keys.

Implement a function to authenticate and retrieve a bearer token using client credentials flow.

Endpoint: POST https://accounts.spotify.com/api/token

Auth: Basic Base64(client_id:client_secret)

Body: grant_type=client_credentials

🎵 Seed Track / Artist Identification
If currently playing track exists, use its title to search for a Spotify track.

Endpoint: GET https://api.spotify.com/v1/search?q={title}&type=track&limit=1

Use artist and track ID from the result as seed inputs.

If mood/genre are provided, compile a list of Spotify genre seeds (Spotify requires specific genres only).

If neither, enter “Surprise me” mode and pull from Spotify’s popular/curated recommendation lists.

🧠 Get Recommendations
Build a call to Spotify’s recommendations endpoint:

GET https://api.spotify.com/v1/recommendations

Parameters:

seed_artists, seed_tracks, seed_genres

Optional: min_energy, target_danceability, max_valence (based on mood)

Parse the response to extract track name and artist.

Combine these into queryable strings for YouTube (e.g. "Apashe - Distance").

📺 YouTube Queue Integration
For each track returned, search using yt_dlp logic already in place.

Use process_play or process_play_next to add to the queue.

Ensure duplicates (by title) are filtered before queuing.

🧪 New Features for Usability (Optional Enhancements)
Add autocomplete on supported Spotify genre tags.

Add toggle options:

/discover surprise_me: true

/discover min_energy: 0.6

/discover limit: 10

Add debug log showing which Spotify seeds and filters were used.

💬 UI/UX Enhancements
Modify followup message to show:

Mood: Happy

Genres: Pop, Indie

Seed Artist: Apashe

Songs Queued: 10

🧪 Testing Tasks
Test command with seed track from queue.

Test with genres and mood only.

Test with "Surprise Me" mode.

Validate YouTube search results and queue population.

Validate auth token refresh logic works and doesn't break under concurrency.

✅ Optional Enhancements:
Add /discover limit: 10 as a parameter

Use Spotify’s energy, valence, danceability filters

Add autocomplete to /discover genres

✅ Overview of the Goal
Implement a robust /discover command for a Discord bot that does the following:

Uses the currently playing track as the discovery base (if no input is given).

Otherwise, uses user-provided artist/song as the seed.

Fetches the artist ID.

Retrieves related artists.

For each related artist, fetches top tracks (limit to 2).

Plays/queues those top tracks.

Optionally supports fetching more tracks by using the related artist graph.

✅ TO-DO LIST

1. Remove Deprecated Logic
   In commands.py or wherever the /discover command is defined:

Remove all calls to get_spotify_recommendations() (deprecated and now returning 404).

Remove logic for:

Using seed_genres or moods.

Constructing Spotify recommendation URL manually.

Retry logic for seed combinations (track+artist, track only, etc).

All error messages about Spotify returning 404 or lack of recommendations.

2. New /discover Slash Command Input Handling
   Keep:

Input parameters: artist_or_song: Optional[str] = None

New logic:

plaintext
Copy
Edit
if artist_or_song is provided:
→ Search Spotify for the track or artist (return artist_id)
elif a track is currently playing:
→ Extract artist from the currently playing entry
else:
→ Return an error saying: "No currently playing song and no artist provided." 3. Artist Lookup Flow
Search Spotify Track endpoint if input is artist_or_song.

Get artist ID and name from first track result.

If using current song, use queue_manager.currently_playing.title to get the track name.

Then search Spotify with that title, same as step 1.

Use existing search_spotify_track(query) helper.

4. Get Related Artists
   Use:

python
Copy
Edit
GET https://api.spotify.com/v1/artists/{id}/related-artists
Extract top 5 artist IDs and names.

Store artist names in a list (can use for logging/display later).

5. Get Top Tracks Per Artist
   For each of the 5 related artist IDs:

Call:

http
Copy
Edit
GET https://api.spotify.com/v1/artists/{id}/top-tracks?market=US
Extract top 2 track names and artist name.

This gives 10 tracks total.

6. Add to Queue
   For each of the 10 tracks:

Combine artist + track name as "{artist} - {track}"

Call your existing process_play(interaction, youtube_title="...") to queue it

Delay with await asyncio.sleep(1) between them if needed to avoid rate limits or processing lag.

7. Optional: Persist Related Artists for Future Expansion
   If you want to allow "more discovery" by branching deeper, store the related artist IDs in memory or cache per user or per guild.

Later, you can let the user say /discover more to:

Pick another artist from the last related artist list

Fetch their related artists

Get their top tracks

And queue those

This allows recursive discovery.

8. Finalize Response
   Send follow-up:

plaintext
Copy
Edit
✅ Discovery mode initiated!
Seed: {original_artist_name}
Related artists discovered: {Artist1}, {Artist2}, ...
Tracks queued: {number}
✅ Summary of Implementation Steps

Step Description
1 Remove all Spotify recommendation logic
2 Extract artist ID from current track or user input
3 Fetch related artists (up to 5)
4 For each related artist, fetch 2 top tracks
5 Call process_play() on each of the 10 track names
6 Send final embedded message to confirm queued songs
7 (optional) Cache artist graph for “/discover more” later

🎯 /discover Command Enhancement: Last.fm Fallback Integration
🛠️ Objective
Implement a fallback mechanism using Last.fm's API to ensure the /discover command remains functional when Spotify's API fails to return results due to deprecations or other issues.

🔄 Updated Workflow
Primary Attempt with Spotify API:

Input Handling:

If the user provides an artist or song name, use it as the seed.

If no input is provided, use the currently playing track as the seed.

Process:

Search for the artist or track on Spotify to obtain the artist_id.

Fetch related artists using Spotify's related-artists endpoint.

Retrieve top tracks for each related artist.

Queue the top tracks for playback.

Fallback to Last.fm API (if Spotify API fails):

Trigger Conditions:

Spotify API returns no results or encounters an error.

Process:

Use the same seed (artist or track name).

Fetch similar artists using Last.fm's artist.getSimilar endpoint.

Retrieve top tracks for each similar artist using artist.getTopTracks.

Queue the top tracks for playback.

🧩 Implementation Steps
Error Handling:

Implement try-except blocks around Spotify API calls.

On exception or empty results, log the issue and proceed to Last.fm fallback.

Last.fm Integration:

Obtain a Last.fm API key and store it securely.

Create functions to interact with artist.getSimilar and artist.getTopTracks endpoints.

Ensure proper formatting of artist and track names to match Last.fm's requirements.

Queue Management:

Modify the queuing logic to handle tracks obtained from both Spotify and Last.fm.

Ensure consistency in how tracks are added to the playback queue, regardless of the source.

User Feedback:

Inform users when the fallback mechanism is triggered.

Provide details about the source of the recommendations (Spotify or Last.fm).

📌 Notes
API Rate Limits:

Monitor and respect rate limits for both Spotify and Last.fm APIs.

Implement caching where appropriate to minimize redundant API calls.

Data Consistency:

Be aware of potential discrepancies in artist and track data between Spotify and Last.fm.

Implement normalization routines to handle such discrepancies.

Testing:

Rigorously test the fallback mechanism to ensure seamless user experience.

Include edge cases where both APIs might fail or return unexpected results.

✅ /discover Command – Logic Flow Overview
This command adds recommended songs to the queue based on:

the currently playing track (if no user input is given)

OR user-provided artist or song name (if provided)

🔁 UNIVERSAL ENTRY LOGIC
python
Copy
Edit
if user_provided_artist_or_song:
seed = user_input
elif currently_playing_track:
seed = currently_playing_track.title
else:
respond("No song is currently playing and no input was provided.")
return
🟩 PRIMARY FLOW — SPOTIFY-BASED LOGIC

1. Search for Track/Artist on Spotify
   python
   Copy
   Edit
   track_info = search_spotify_track(seed)
   if not track_info:
   Fallback to Last.fm
   Return object:

json
Copy
Edit
{
"track_name": "Enter Sandman",
"artist_name": "Metallica",
"artist_id": "spotify:artist:xyz"
} 2. Get Related Artists from Spotify
python
Copy
Edit
related_artists = get_spotify_related_artists(track_info.artist_id)
if not related_artists:
Fallback to Last.fm 3. Get Top Tracks for Related Artists
python
Copy
Edit
recommendations = []
for artist_id in related_artists[:5]:
tracks = get_spotify_top_tracks(artist_id)
recommendations.extend(tracks[:2]) 4. Add to Queue
python
Copy
Edit
for track in recommendations:
await process_play(interaction, youtube_title=track["name"] + " - " + track["artist"])
🟥 FALLBACK FLOW — LAST.FM-BASED LOGIC

1. Search for Artist Name on Last.fm
   python
   Copy
   Edit
   lastfm_artist = extract_artist_name(seed)
2. Fetch Similar Artists
   python
   Copy
   Edit
   similar_artists = get_lastfm_similar_artists(lastfm_artist)
   if not similar_artists:
   respond("No similar artists found on Last.fm.")
   return
   Example return:

json
Copy
Edit
["Slipknot", "Avenged Sevenfold", "Trivium", "Bullet For My Valentine"] 3. Get Top Tracks for Each Artist
python
Copy
Edit
recommendations = []
for artist in similar_artists[:5]:
tracks = get_lastfm_top_tracks(artist)
recommendations.extend(tracks[:2])
Track return:

json
Copy
Edit
[{"artist": "Trivium", "title": "In Waves"}, {"artist": "Trivium", "title": "Strife"}] 4. Add to Queue
python
Copy
Edit
for track in recommendations:
await process_play(interaction, youtube_title=track["artist"] + " - " + track["title"])
⚠️ Error Resilience Summary
Spotify API returns no results → fallback to Last.fm

If Last.fm also returns nothing → gracefully notify the user

Track parsing issues, unavailable YouTube videos, or errors in process_play → log and skip without halting

💡 Bonus Behavior: When User Wants More
Trigger
User presses a “🔁 Discover More” button or reuses /discover.

Logic
Pick a random or next artist from the original related list (Spotify or Last.fm cache).

Repeat steps 2–4 of the corresponding flow.

🧪 Example Output (User Input: "Bring Me The Horizon")
text
Copy
Edit
🎵 Found: Bring Me The Horizon
🔁 Getting Related Artists from Spotify...

✅ Similar artists:

- Asking Alexandria
- I Prevail
- Motionless In White
  ...

🎧 Top Tracks:
• Asking Alexandria - Alone In A Room
• I Prevail - Hurricane
• Motionless In White - Another Life
...

🪄 Added 6 new songs to your queue. Type /discover again to keep exploring!

✅ /discover Command – Logic Flow Overview
This command adds recommended songs to the queue based on:

the currently playing track (if no user input is given)

OR user-provided artist or song name (if provided)

🔁 UNIVERSAL ENTRY LOGIC
python
Copy
Edit
if user_provided_artist_or_song:
seed = user_input
elif currently_playing_track:
seed = currently_playing_track.title
else:
respond("No song is currently playing and no input was provided.")
return
🟩 PRIMARY FLOW — SPOTIFY-BASED LOGIC

1. Search for Track/Artist on Spotify
   python
   Copy
   Edit
   track_info = search_spotify_track(seed)
   if not track_info:
   Fallback to Last.fm
   Return object:

json
Copy
Edit
{
"track_name": "Enter Sandman",
"artist_name": "Metallica",
"artist_id": "spotify:artist:xyz"
} 2. Get Related Artists from Spotify
python
Copy
Edit
related_artists = get_spotify_related_artists(track_info.artist_id)
if not related_artists:
Fallback to Last.fm 3. Get Top Tracks for Related Artists
python
Copy
Edit
recommendations = []
for artist_id in related_artists[:5]:
tracks = get_spotify_top_tracks(artist_id)
recommendations.extend(tracks[:2]) 4. Add to Queue
python
Copy
Edit
for track in recommendations:
await process_play(interaction, youtube_title=track["name"] + " - " + track["artist"])
🟥 FALLBACK FLOW — LAST.FM-BASED LOGIC

1. Search for Artist Name on Last.fm
   python
   Copy
   Edit
   lastfm_artist = extract_artist_name(seed)
2. Fetch Similar Artists
   python
   Copy
   Edit
   similar_artists = get_lastfm_similar_artists(lastfm_artist)
   if not similar_artists:
   respond("No similar artists found on Last.fm.")
   return
   Example return:

json
Copy
Edit
["Slipknot", "Avenged Sevenfold", "Trivium", "Bullet For My Valentine"] 3. Get Top Tracks for Each Artist
python
Copy
Edit
recommendations = []
for artist in similar_artists[:5]:
tracks = get_lastfm_top_tracks(artist)
recommendations.extend(tracks[:2])
Track return:

json
Copy
Edit
[{"artist": "Trivium", "title": "In Waves"}, {"artist": "Trivium", "title": "Strife"}] 4. Add to Queue
python
Copy
Edit
for track in recommendations:
await process_play(interaction, youtube_title=track["artist"] + " - " + track["title"])
⚠️ Error Resilience Summary
Spotify API returns no results → fallback to Last.fm

If Last.fm also returns nothing → gracefully notify the user

Track parsing issues, unavailable YouTube videos, or errors in process_play → log and skip without halting

💡 Bonus Behavior: When User Wants More
Trigger
User presses a “🔁 Discover More” button or reuses /discover.

Logic
Pick a random or next artist from the original related list (Spotify or Last.fm cache).

Repeat steps 2–4 of the corresponding flow.

🧪 Example Output (User Input: "Bring Me The Horizon")
text
Copy
Edit
🎵 Found: Bring Me The Horizon
🔁 Getting Related Artists from Spotify...

✅ Similar artists:

- Asking Alexandria
- I Prevail
- Motionless In White
  ...

🎧 Top Tracks:
• Asking Alexandria - Alone In A Room
• I Prevail - Hurricane
• Motionless In White - Another Life
...

🪄 Added 6 new songs to your queue. Type /discover again to keep exploring!

🧠 Project Goal
Enhance the /discover command by:

Using Spotify's API to recommend music.

Falling back to Last.fm if Spotify fails.

Automatically queuing tracks on YouTube based on artist similarity.

🔐 Authentication
Register Spotify app at Spotify Developer Dashboard.

Store SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env.

Authenticate using Client Credentials Flow.

🧪 Input Handling
If user provides artist or song: use that as the seed.

Else if a song is currently playing: extract artist name.

Else: show error → “No input provided and no song playing.”

🎵 Spotify Discovery Logic
Search for Seed Artist/Track
GET /v1/search?q={query}&type=track&limit=1

Get Related Artists
GET /v1/artists/{id}/related-artists

Fetch Top Tracks (2 per related artist)
GET /v1/artists/{id}/top-tracks?market=US

Queue Results via YouTube
For each: "{artist} - {track}" → process_play()

🟥 Fallback: Last.fm Logic
Search Artist Name
Use seed to extract clean artist name.

Get Similar Artists
artist.getSimilar

Fetch Top Tracks per Artist
artist.getTopTracks

Queue to YouTube
Same format: "{artist} - {track}" → process_play()

⚠️ Error Resilience
Spotify fails → fallback to Last.fm.

Last.fm fails → notify user.

Log all issues without crashing command.

💬 User Feedback
Confirm queued tracks.

Show:

Mood (if used)

Genres (if used)

Seed artist

Number of songs queued

Message is ephemeral.

🧰 Refactoring Tasks
❌ Remove deprecated logic:

get_spotify_recommendations()

Seed/mood combo retry logic

404 Spotify fallback errors

✅ Add new logic:

Seed resolution

Related artist → top tracks → YouTube queue

🌱 Surprise Me Mode
If no input: use trending/popular Spotify content (optional).

Later: add support for energy, valence, danceability filters.

🧪 Testing Checklist
/discover with current track → ✅ queues results.

/discover with user input → ✅ queues results.

Spotify fails → Last.fm fallback works.

Track titles format correctly for YouTube.

Token refresh works without crashing.

🌀 Extra Features
Cache related artists for "Discover More" button.

Autocomplete supported Spotify genre tags.

Slash command options:

limit: 10

surprise_me: true

min_energy: 0.6
