import yt_dlp

def test_youtube_cookies(cookiefile_path: str, search_term: str):
    ydl_opts = {
        'quiet': True,
        'cookiefile': cookiefile_path,
        'format': 'bestaudio/best',
        'noplaylist': True,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        }
    }

    query = f'ytsearch1:{search_term}'
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if not info or 'entries' not in info or not info['entries'] or info['entries'][0] is None:
                print("❌ Search failed or returned no results.")
            else:
                print(f"✅ Found video: {info['entries'][0]['title']}")
    except Exception as e:
        print(f"⚠️ Error testing cookies: {e}")

# Example usage:
test_youtube_cookies(
    "cookies.txt",
    "better than you our last night"
)
