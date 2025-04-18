# Testing the /off_brand_pandora Command

This document outlines the testing procedures for the `/off_brand_pandora` command implementation.

## Test Cases

### 1. Basic Functionality Tests

- [ ] Test with mood parameter only
  - Command: `/off_brand_pandora mood:happy`
  - Expected: Bot should find tracks based on the happy mood tag

- [ ] Test with genres parameter only
  - Command: `/off_brand_pandora genres:rock,electronic`
  - Expected: Bot should find tracks based on rock and electronic genres

- [ ] Test with both parameters
  - Command: `/off_brand_pandora mood:chill genres:jazz,lofi`
  - Expected: Bot should find tracks based on both the chill mood and jazz/lofi genres

- [ ] Test with neither parameter (fallback to current song)
  - Command: `/off_brand_pandora`
  - Expected: Bot should use the currently playing song as a seed for recommendations

### 2. Error Handling Tests

- [ ] Test with invalid mood/genre
  - Command: `/off_brand_pandora mood:xyznonexistent`
  - Expected: Bot should handle the error gracefully and attempt to find alternative tracks

- [ ] Test with no current song and no parameters
  - Command: `/off_brand_pandora` (when nothing is playing)
  - Expected: Bot should inform the user that no recommendations could be found

- [ ] Test with "Various Artists" as current artist
  - Setup: Play a song with "Various Artists" as the artist
  - Command: `/off_brand_pandora`
  - Expected: Bot should skip using the seed artist and rely on mood/genre or inform the user

### 3. Memory Management Tests

- [ ] Test cancellation of existing task
  - Steps:
    1. Run `/off_brand_pandora mood:happy`
    2. While tracks are being queued, run `/off_brand_pandora mood:sad`
  - Expected: The first task should be cancelled, and only tracks from the second command should be queued

### 4. YouTube Handling Tests

- [ ] Test handling of age-restricted content
  - Setup: Find a known age-restricted YouTube video
  - Steps: Use that artist/title as a seed for recommendations
  - Expected: Bot should be able to queue tracks without being blocked by age restrictions

- [ ] Test handling of bot detection
  - Expected: Bot should use enhanced options to bypass bot detection mechanisms

## Verification Checklist

- [ ] Tracks are properly deduplicated in the final queue
- [ ] Error handling provides meaningful messages to users
- [ ] "Various Artists" and "[unknown]" artist results are properly handled
- [ ] YouTube title fallback logic handles edge cases
- [ ] Mood/genre-based lookups are properly combined with artist-based recommendations
- [ ] Proper fallback logic works when mood/genre/seed results fail
- [ ] Tracks queue without interrupting ongoing playback
- [ ] Pandora tasks are properly stored and managed per guild_id
- [ ] Existing tasks are properly cancelled and replaced
