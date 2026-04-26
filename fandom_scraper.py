import urllib.request
import urllib.parse
import json
from bs4 import BeautifulSoup
import re
import argparse
import time

def get_page_data(wiki_domain, page_name):
    """
    Fetches the parsed HTML data from the Fandom API.
    Fandom API doesn't trigger Cloudflare's browser blocks.
    """
    api_url = f"https://{wiki_domain}/api.php?action=parse&page={urllib.parse.quote(page_name)}&format=json"
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    try:
        response = urllib.request.urlopen(req).read()
        data = json.loads(response)
        if "error" in data:
            # Fallback for pages that might have "_(episode)" suffix
            api_url = f"https://{wiki_domain}/api.php?action=parse&page={urllib.parse.quote(page_name + '_(episode)')}&format=json"
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            response = urllib.request.urlopen(req).read()
            data = json.loads(response)

        return data.get("parse", {}).get("text", {}).get("*", "")
    except Exception as e:
        print(f"Error fetching {page_name}: {e}")
        return ""

def extract_images(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    images = []
    for img in soup.find_all('img'):
        src = img.get('src', '')
        data_src = img.get('data-src', '')
        real_src = data_src if data_src else src

        # Filter out UI icons (like padlock, category icons)
        if real_src and real_src.startswith('http') and 'Padlock' not in real_src and 'Real-world.png' not in real_src:
            # Remove scaling parameters to get original quality
            clean_src = real_src.split('/revision/')[0] if '/revision/' in real_src else real_src
            if clean_src not in images:
                images.append(clean_src)
    return images

def extract_transcript(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    dialogues = []

    # Most Fandom transcripts use wikitables
    tables = soup.find_all('table', class_='wikitable')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all(['th', 'td'])
            if len(cols) == 2:
                speaker = cols[0].get_text(separator=' ', strip=True)
                text = cols[1].get_text(separator=' ', strip=True)
                if speaker == "":
                    dialogues.append(f"[Action] {text}")
                else:
                    dialogues.append(f"{speaker}: {text}")
            elif len(cols) == 1:
                text = cols[0].get_text(separator=' ', strip=True)
                dialogues.append(f"[Action] {text}")

    # Cleanup spacing inside brackets
    cleaned_dialogues = []
    for d in dialogues:
        d = re.sub(r' \]', ']', d)
        d = re.sub(r'\[ ', '[', d)
        cleaned_dialogues.append(d)

    return cleaned_dialogues

def main():
    parser = argparse.ArgumentParser(description="Fandom Transcript Scraper for Language Learning")
    parser.add_argument("--wiki", required=True, help="Wiki domain (e.g., avatar.fandom.com)")
    parser.add_argument("--episode", required=True, help="Name of the episode (e.g., 'The Blind Bandit')")
    parser.add_argument("--output", default="output.txt", help="Output file name")
    parser.add_argument("--prefix", default="", help="Prefix for the title (e.g., 'S2-Chapter 6')")
    args = parser.parse_args()

    page_name = args.episode.replace(" ", "_")
    transcript_page_name = f"Transcript:{page_name}"

    print(f"[*] Fetching images for '{args.episode}'...")
    main_html = get_page_data(args.wiki, page_name)
    images = extract_images(main_html)

    print(f"[*] Fetching transcript for '{args.episode}'...")
    transcript_html = get_page_data(args.wiki, transcript_page_name)
    dialogues = extract_transcript(transcript_html)

    if not dialogues:
        print("[!] No dialogues found! The wiki might format transcripts differently (e.g., paragraphs instead of tables).")
        return

    total_dialogues = len(dialogues)
    total_images = len(images)
    interval = max(1, total_dialogues // total_images) if total_images > 0 else total_dialogues + 1

    print(f"[*] Saving to {args.output}...")
    with open(args.output, "w", encoding="utf-8") as f:
        title = f"{args.prefix}: {args.episode}" if args.prefix else args.episode
        f.write(f"{title}\n\n")

        img_idx = 0
        for i, d in enumerate(dialogues):
            # Insert images evenly
            if img_idx < total_images and i > 0 and i % interval == 0:
                f.write(f"![Image]({images[img_idx]})\n\n")
                img_idx += 1
            f.write(d + "\n\n")

    print(f"[+] Done! Saved {len(dialogues)} lines and {img_idx} images.")

if __name__ == "__main__":
    main()
