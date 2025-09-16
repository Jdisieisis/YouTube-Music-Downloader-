import pytube
import os
import re
import logging
from string import punctuation
from tqdm import tqdm
from multiprocessing.pool import ThreadPool
import validators
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_filename(filename):
    """Remove invalid characters from the filename."""
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1F\x7F-\xFF]', '', filename)
    return filename.strip()

def truncate_title(title, max_length=20):
    """Truncate the title to a maximum length."""
    if len(title) > max_length:
        title = title[:max_length]
    return title

def add_banner():
    """Display the program banner."""
    banner = """
╭━━━┳━━┳╮╱╱╭━━━┳━╮╱╭┳━━━━╮
┃╭━╮┣┫┣┫┃╱╱┃╭━━┫┃╰╮┃┃╭╮╭╮┃
┃╰━━╮┃┃┃┃╱╱┃╰━━┫╭╮╰╯┣╯┃┃╰╯
╰━━╮┃┃┃┃┃╱╭┫╭━━┫┃╰╮┃┃╱┃┃
┃╰━╯┣┫┣┫╰━╯┃╰━━┫┃╱┃┃┃╱┃┃
╰━━━┻━━┻━━━┻━━━┻╯╱╰━╯╱╰╯
          Youtube Music Downloader 1.20
                     xXSILENTXx
"""
    print(banner)

def download_video(video, out_path, your_name, audio_quality="highest"):
    """Download a single YouTube video as audio."""
    try:
        # Get audio stream based on quality preference
        if audio_quality == "highest":
            audio = video.streams.filter(only_audio=True).order_by('abr').desc().first()
        else:
            audio = video.streams.filter(only_audio=True).order_by('abr').asc().first()
            
        video_title = sanitize_filename(video.title.strip().translate(str.maketrans('', '', punctuation)))
        channel_name = sanitize_filename(video.author.strip().translate(str.maketrans('', '', punctuation)))
        
        # Let user choose whether to truncate title
        if input(f"Truncate title '{video_title}'? (y/n): ").lower() == 'y':
            truncated_title = truncate_title(video_title)
        else:
            truncated_title = video_title
            
        filename = f"{truncated_title} By {channel_name} ~ {your_name}.mp3"
        file_path = os.path.join(out_path, filename)
        
        # Show progress for single video download
        with tqdm(total=100, desc=f"Downloading {filename}") as pbar:
            audio.download(output_path=out_path, filename=filename)
            pbar.update(100)
            
        logging.info(f"Downloaded: {filename}")
        return True
    except Exception as e:
        logging.error(f"Failed to download video: {e}")
        return False

def download_playlist(playlist, out_path, your_name, audio_quality="highest", max_workers=4):
    """Download a YouTube playlist as audio files."""
    try:
        logging.info("Downloading playlist...")
        
        # Create a ThreadPool with specified number of workers
        pool = ThreadPool(processes=max_workers)
        
        results = []
        for video in tqdm(playlist.videos, desc="Processing", unit="video"):
            result = pool.apply_async(download_video, (video, out_path, your_name, audio_quality), 
                                    error_callback=logging.error)
            results.append(result)
        
        pool.close()
        pool.join()
        
        # Check if all downloads were successful
        success_count = sum(1 for r in results if r.successful())
        logging.info(f"Playlist download complete. {success_count}/{len(results)} videos downloaded successfully.")
    except Exception as e:
        logging.error(f"Failed to download playlist: {e}")

def get_user_input(prompt, validator=None, default=None):
    """Get and validate user input."""
    while True:
        user_input = input(prompt).strip()
        
        if not user_input and default is not None:
            return default
            
        if validator is None or validator(user_input):
            return user_input
            
        logging.error("Invalid input, please try again.")

def main():
    """Main program function."""
    add_banner()
    
    # Get link from user with validation
    link = get_user_input(
        "Please enter a YouTube video or playlist link (or 'quit' to exit): ",
        lambda x: x.lower() in ('quit', 'exit') or validators.url(x)
    )
    
    if link.lower() in ('quit', 'exit'):
        logging.info("Exiting program.")
        sys.exit(0)
    
    # Get output path
    out_path = get_user_input("Enter folder path or press enter for current: ", default=os.getcwd())
    
    # Get your name
    your_name = get_user_input("Enter your name or press enter for default: ", default="xXSILENTXx")
    
    # Get audio quality preference
    audio_quality = get_user_input(
        "Select audio quality (highest/lowest) or press enter for default: ",
        lambda x: x.lower() in ('highest', 'lowest', ''),
        default="highest"
    )
    
    # Get worker count for playlists
    max_workers = get_user_input(
        "Number of download threads for playlists (1-10) or press enter for default: ",
        lambda x: x.isdigit() and 1 <= int(x) <= 10 or x == '',
        default="4"
    )
    max_workers = int(max_workers)
    
    # Process the link
    try:
        if 'playlist' in link.lower():
            playlist = pytube.Playlist(link)
            download_playlist(playlist, out_path, your_name, audio_quality, max_workers)
        else:
            video = pytube.YouTube(link)
            download_video(video, out_path, your_name, audio_quality)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    
    logging.info("Done!")

if __name__ == '__main__':
    main()
