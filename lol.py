import pytube
import os
import re
import logging
from string import punctuation
from tqdm import tqdm
from multiprocessing.pool import ThreadPool
import validators

logging.basicConfig(level=logging.INFO)

def sanitize_filename(filename):
    # Remove invalid characters from the filename
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1F\x7F-\xFF]', '', filename)
    return filename

def truncate_title(title, max_length):
    # Truncate the title to a maximum length
    if len(title) > max_length:
        title = title[:max_length] + ""
    return title

def add_banner():
    banner = """
╭━━━┳━━┳╮╱╱╭━━━┳━╮╱╭┳━━━━╮
┃╭━╮┣┫┣┫┃╱╱┃╭━━┫┃╰╮┃┃╭╮╭╮┃
┃╰━━╮┃┃┃┃╱╱┃╰━━┫╭╮╰╯┣╯┃┃╰╯
╰━━╮┃┃┃┃┃╱╭┫╭━━┫┃╰╮┃┃╱┃┃
┃╰━╯┣┫┣┫╰━╯┃╰━━┫┃╱┃┃┃╱┃┃
╰━━━┻━━┻━━━┻━━━┻╯╱╰━╯╱╰╯
          Youtube Music Downloder 1.20
                     xXSILENTXx
"""
    print(banner)

def download_video(video, out_path, your_name):
    try:
        audio = video.streams.filter(only_audio=True).first()
        video_title = sanitize_filename(video.title.strip().translate(str.maketrans('', '', punctuation)))
        channel_name = sanitize_filename(video.author.strip().translate(str.maketrans('', '', punctuation)))
        truncated_title = truncate_title(video_title, 20)  # Set the maximum title length to 20 characters
        filename = f"{truncated_title} By {channel_name} ~ {your_name}.mp3"
        file_path = os.path.join(out_path, filename)
        audio.download(output_path=out_path, filename=filename)
        logging.info(f"Downloaded: {filename}")
    except pytube.exceptions.PytubeError as e:
        logging.error(f"Failed to download video: {e}")

def download_playlist(playlist, out_path, your_name):
    try:
        logging.info("Downloading playlist...")

        # Create a ThreadPool with 4 workers for parallel downloads
        pool = ThreadPool(processes=4)

        for video in tqdm(playlist.videos, desc="Downloading", unit="video"):
            pool.apply_async(download_video, (video, out_path, your_name), error_callback=logging.error)

        pool.close()
        pool.join()

        logging.info("Playlist download complete.")
    except pytube.exceptions.PytubeError as e:
        logging.error(f"Failed to download playlist: {e}")

def main():
    add_banner()

    while True:
        # Get link from user
        link = input("Please enter a YouTube video or playlist link: ")

        # Validate the link
        if not validators.url(link):
            logging.error("Invalid link, please try again.")
            continue

        break

    # Get output path from user or use the current directory
    out_path = input("Enter folder path or press enter for current: ")
    out_path = out_path.strip() if out_path else os.getcwd()

    # Get your name from user
    your_name = ("xXSILENTXx")

    if 'playlist' in link.lower():
        playlist = pytube.Playlist(link)
        download_playlist(playlist, out_path, your_name)
    else:
        video = pytube.YouTube(link)
        download_video(video, out_path, your_name)

    logging.info("Done!")

if __name__ == '__main__':
    main()