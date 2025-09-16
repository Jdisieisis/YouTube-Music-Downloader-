import pytube
import os
import re
import logging
from string import punctuation
from tqdm import tqdm
from multiprocessing.pool import ThreadPool
import validators
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TCON
from mutagen.mp3 import MP3
import sys

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
          Youtube Music Downloader 1.30
        Car Stereo Compatible Edition
                     xXSILENTXx
"""
    print(banner)

def add_id3_tags(file_path, title, artist, album="YouTube", track_number=""):
    """Add ID3 tags to MP3 file for car stereo compatibility."""
    try:
        # Load the file with EasyID3 for simple tag management
        audio = MP3(file_path, ID3=EasyID3)
        
        # Add basic tags
        audio['title'] = title
        audio['artist'] = artist
        audio['album'] = album
        audio['genre'] = 'YouTube'
        
        if track_number:
            audio['tracknumber'] = track_number
        
        # Save EasyID3 tags
        audio.save()
        
        # Now add ID3v2.3 tags using the full ID3 interface for better compatibility
        audio_id3 = ID3(file_path)
        
        # Remove existing frames to avoid duplicates
        audio_id3.delall('TIT2')  # Title
        audio_id3.delall('TPE1')  # Artist
        audio_id3.delall('TALB')  # Album
        audio_id3.delall('TRCK')  # Track
        audio_id3.delall('TCON')  # Genre
        
        # Add ID3v2.3 frames with proper encoding
        audio_id3.add(TIT2(encoding=3, text=title))  # Title
        audio_id3.add(TPE1(encoding=3, text=artist))  # Artist
        audio_id3.add(TALB(encoding=3, text=album))  # Album
        audio_id3.add(TCON(encoding=3, text='YouTube'))  # Genre
        
        if track_number:
            audio_id3.add(TRCK(encoding=3, text=track_number))  # Track
        
        # Save with both ID3v2.3 and ID3v1 tags for maximum compatibility
        # v2_version=3 for ID3v2.3 (most compatible)
        # v1=2 to create/update ID3v1 tags (essential for older car stereos)
        audio_id3.save(v2_version=3, v1=2)
        
        logging.info(f"Added ID3 tags to: {os.path.basename(file_path)}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to add ID3 tags to {file_path}: {e}")
        return False

def download_video(video, out_path, your_name, track_number=""):
    """Download a single YouTube video as audio with proper ID3 tags."""
    try:
        # Get the highest quality audio stream
        audio = video.streams.filter(only_audio=True).order_by('abr').desc().first()
        
        # Sanitize title and artist names
        video_title = sanitize_filename(video.title.strip().translate(str.maketrans('', '', punctuation)))
        channel_name = sanitize_filename(video.author.strip().translate(str.maketrans('', '', punctuation)))
        
        # Truncate title if needed
        truncated_title = truncate_title(video_title)
        
        # Create filename
        filename = f"{truncated_title} By {channel_name} ~ {your_name}.mp3"
        file_path = os.path.join(out_path, filename)
        
        # Download the audio file
        logging.info(f"Downloading: {filename}")
        audio.download(output_path=out_path, filename=filename)
        
        # Add ID3 tags for car stereo compatibility
        add_id3_tags(file_path, video_title, channel_name, "YouTube", track_number)
        
        logging.info(f"Successfully downloaded and tagged: {filename}")
        return True
        
    except pytube.exceptions.PytubeError as e:
        logging.error(f"Failed to download video: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error downloading video: {e}")
        return False

def download_playlist(playlist, out_path, your_name, max_workers=4):
    """Download a YouTube playlist as audio files with proper ID3 tags."""
    try:
        logging.info("Downloading playlist...")
        
        # Create a ThreadPool with specified number of workers
        pool = ThreadPool(processes=max_workers)
        
        results = []
        for i, video in enumerate(tqdm(playlist.videos, desc="Downloading", unit="video"), 1):
            # Pass track number for proper tagging
            result = pool.apply_async(download_video, (video, out_path, your_name, str(i)), 
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
            download_playlist(playlist, out_path, your_name, max_workers)
        else:
            video = pytube.YouTube(link)
            download_video(video, out_path, your_name)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    
    logging.info("Done! Your downloaded files should now be compatible with older car stereos.")

if __name__ == '__main__':
    main()
