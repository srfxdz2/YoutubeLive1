import os
from yt_dlp import YoutubeDL

# Define the playlist URL and output directory
playlist_url = "https://www.youtube.com/playlist?list=PLEekr8MhjAeQtCjBrGNAKfsT-9ol969hb"
output_dir = "yt_music"
os.makedirs(output_dir, exist_ok=True)

def download():
    # Step 1: Extract playlist info to filter out video #44
    with YoutubeDL({'quiet': True}) as ydl:
        playlist_info = ydl.extract_info(playlist_url, download=False)
        video_entries = playlist_info['entries']
    
    # Filter out video #44 (index 43 as Python uses zero-based indexing)
    video_urls = [
        entry['url'] for i, entry in enumerate(video_entries) if i != 43
    ]

    print(f"Total videos to download (excluding #44): {len(video_urls)}")

    # Step 2: yt-dlp options for maximum performance and full resolution
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Full resolution
        'outtmpl': os.path.join(output_dir, '%(playlist_index)s - %(title)s.%(ext)s'),  # Organized filenames
        'merge_output_format': 'mp4',  # Output format
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # Ensure mp4 format
        }],
        'n_threads': 16,  # Use 16 threads for faster download
        'progress_hooks': [lambda d: print(f"Status: {d['status']} - {d.get('filename', '')}")],
        'concurrent_fragment_downloads': 4,  # Download 4 fragments concurrently per video
        'postprocessor_args': [
            '-threads', '8',  # Enable multi-threading in FFmpeg postprocessing
        ],
    }

    # Step 3: Download remaining videos
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download(video_urls)

# Call the download function
if __name__ == "__main__":
    download()
