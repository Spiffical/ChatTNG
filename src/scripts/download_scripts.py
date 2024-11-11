import requests
from bs4 import BeautifulSoup
import re
import os
import time
from pathlib import Path
import argparse
from typing import List, Tuple

def get_episode_mapping():
    """Returns the correct episode mapping for TNG"""
    season_episodes = {
        1: list(range(1, 26)),      # 25 episodes (pilot is 1-2)
        2: list(range(27, 49)),     # 22 episodes
        3: list(range(49, 75)),     # 26 episodes
        4: list(range(75, 101)),    # 26 episodes
        5: list(range(101, 127)),   # 26 episodes
        6: list(range(127, 153)),   # 26 episodes
        7: list(range(153, 179))    # 26 episodes (including two-part finale)
    }
    return season_episodes

def get_episode_list() -> List[Tuple[int, int, str]]:
    """
    Scrapes the episode list and returns a list of (season, episode, url) tuples
    """
    url = "http://www.chakoteya.net/NextGen/episodes.htm"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    episodes = []
    current_season = 1
    episode_in_season = 1
    
    # Find all links in the document
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and href.endswith('.htm') and href != 'episodes.htm':
            script_number = href.replace('.htm', '')
            full_url = f"http://www.chakoteya.net/NextGen/{script_number}.htm"
            
            episodes.append((current_season, episode_in_season, full_url))
            episode_in_season += 1
            
            # Check for season boundaries based on episode count
            if (current_season == 1 and episode_in_season > 25) or \
               (current_season == 2 and episode_in_season > 22) or \
               (current_season >= 3 and episode_in_season > 26):
                current_season += 1
                episode_in_season = 1
    
    return episodes

def download_and_clean_script(url: str, output_path: str):
    """
    Downloads a script from chakoteya.net and cleans it for parsing
    """
    # Add delay to be respectful to the server
    time.sleep(1)
    
    try:
        # Download the content
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main content table
        content = soup.find('table')
        if not content:
            print(f"Warning: Could not find script content for {url}")
            return False
        
        # Extract the raw text
        raw_text = content.get_text()
        
        # Clean up the text:
        # 1. Remove stage directions in brackets
        text = re.sub(r'\[.*?\]', '', raw_text)
        
        # 2. Remove empty lines and extra whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 3. Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"Successfully downloaded: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Download Star Trek TNG scripts')
    parser.add_argument('output_dir', help='Directory to save the script files')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get episode list
    print("Fetching episode list...")
    episodes = get_episode_list()
    
    # Download each episode
    successful = 0
    failed = 0
    
    for season, episode, url in episodes:
        # Create filename in format S01E01.txt
        filename = f"S{season:02d}E{episode:02d}.txt"
        output_path = output_dir / filename
        
        print(f"\nDownloading {filename} from {url}")
        if download_and_clean_script(url, output_path):
            successful += 1
        else:
            failed += 1
    
    print(f"\nDownload complete!")
    print(f"Successfully downloaded: {successful} episodes")
    print(f"Failed downloads: {failed} episodes")

if __name__ == "__main__":
    main()