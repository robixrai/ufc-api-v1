#!/usr/bin/env python3
"""
UFC Fighter Photo Web Scraper
Scrapes official fighter images directly from ufc.com
No API key required - just pure web scraping
"""

import requests
from bs4 import BeautifulSoup
import json
import sys
from pathlib import Path
from urllib.parse import urljoin
import time

# Get the project root (parent of scripts folder)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# UFC base URL
UFC_BASE = "https://www.ufc.com"
UFC_ATHLETE = f"{UFC_BASE}/athlete"

# Headers to avoid being blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def normalize_fighter_name(fighter_name: str) -> str:
    """
    Convert fighter name to UFC URL format.
    Example: "Jon Jones" -> "jon-jones"
    """
    return fighter_name.lower().replace(" ", "-").replace(".", "")


def scrape_fighter_page(fighter_name: str) -> dict:
    """
    Scrape UFC athlete page and extract fighter images.

    Args:
        fighter_name: Fighter's name (e.g., "Jon Jones")

    Returns:
        dict with fighter_name, ufc_url, images, and status
    """

    # Construct UFC URL
    normalized_name = normalize_fighter_name(fighter_name)
    ufc_url = f"{UFC_ATHLETE}/{normalized_name}"

    result = {
        "fighter_name": fighter_name,
        "ufc_url": ufc_url,
        "images": [],
        "headshot": None,
        "profile_images": [],
        "status": "not_found"
    }

    try:
        print(f"  Scraping: {ufc_url}")
        response = requests.get(ufc_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Try multiple selectors to find fighter images
        image_selectors = [
            # Look for img tags with specific attributes
            'img[src*="/athlete"]',
            'img[alt*="fighter"]',
            'img.fighter-image',
            'img[data-testid*="fighter"]',
            # Generic high-res images
            'img[src$=".jpg"]',
            'img[src$=".png"]'
        ]

        images_found = set()  # Use set to avoid duplicates

        # Extract images
        for selector in image_selectors:
            images = soup.select(selector)
            for img in images:
                src = img.get('src', '')
                alt = img.get('alt', '').lower()

                # Filter for likely fighter photos
                if src and (
                        'athlete' in src.lower() or
                        'fighter' in alt or
                        'headshot' in alt.lower() or
                        'ufc.com' in src
                ):
                    # Convert relative URLs to absolute
                    if src.startswith('/'):
                        src = urljoin(UFC_BASE, src)

                    # Filter out tiny images and tracking pixels
                    if 'image' in src.lower() or 'photo' in src.lower():
                        images_found.add(src)

        # Also check for images in specific containers
        fighter_containers = soup.find_all(['div', 'section'], class_=lambda x: x and 'fighter' in x.lower())
        for container in fighter_containers:
            for img in container.find_all('img'):
                src = img.get('src', '')
                if src and src.startswith(('http', '/')):
                    if src.startswith('/'):
                        src = urljoin(UFC_BASE, src)
                    if 'cdn' in src or 'ufc.com' in src:
                        images_found.add(src)

        # Try to find the main profile image (usually in meta tags or hero section)
        meta_image = soup.find('meta', property='og:image')
        if meta_image and meta_image.get('content'):
            images_found.add(meta_image['content'])

        # Convert set to list
        result["images"] = list(images_found)

        if result["images"]:
            result["headshot"] = result["images"][0]  # First image as primary
            result["profile_images"] = result["images"][1:] if len(result["images"]) > 1 else []
            result["status"] = "found"
            return result
        else:
            result["status"] = "page_found_no_images"
            return result

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            result["status"] = "fighter_not_found_404"
        else:
            result["status"] = f"http_error_{response.status_code}"
        return result
    except Exception as e:
        result["status"] = f"error: {str(e)}"
        return result


def load_fighters_from_file() -> list:
    """Load fighter names from data/fighters.txt"""
    file_path = DATA_DIR / "fighters.txt"

    if not file_path.exists():
        # Create example file
        example_content = """# Add fighter names below (one per line)
# Example:
Conor McGregor
Jon Jones
Kamaru Usman
"""
        file_path.write_text(example_content)
        print(f"Created example file: {file_path}")
        print("Add fighter names (one per line) and run again.\n")
        return []

    # Read fighters from file
    fighters = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                fighters.append(line)

    return fighters


def scrape_fighters(fighters: list) -> list:
    """Scrape multiple fighters and return results."""
    results = []

    for i, fighter_name in enumerate(fighters, 1):
        print(f"[{i}/{len(fighters)}] {fighter_name}")
        result = scrape_fighter_page(fighter_name)
        results.append(result)

        # Print status
        if result["status"] == "found":
            print(f"  ✓ Found {len(result['images'])} images")
        else:
            print(f"  ✗ Status: {result['status']}")

        # Be nice to the server - small delay between requests
        time.sleep(1)

    return results


def save_results_json(results: list):
    """Save results to JSON file in data folder."""
    output_path = DATA_DIR / "fighter_photos.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Results saved to {output_path}")


def main():
    """Main scraper function."""

    print("=" * 70)
    print("UFC Fighter Photo Web Scraper")
    print("=" * 70)
    print(f"Data folder: {DATA_DIR}\n")

    # Load fighters
    fighters = load_fighters_from_file()

    if not fighters:
        print("❌ No fighters found to process.")
        sys.exit(1)

    print(f"✓ Loaded {len(fighters)} fighters from data/fighters.txt")
    print("-" * 70)
    print()

    # Scrape fighters
    results = scrape_fighters(fighters)

    # Save results
    print("\n" + "=" * 70)
    save_results_json(results)

    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("-" * 70)

    found_count = sum(1 for r in results if r["status"] == "found")
    not_found = sum(1 for r in results if "not_found" in r["status"])

    for result in results:
        status = "✓" if result["status"] == "found" else "✗"
        image_count = len(result.get("images", []))
        print(f"{status} {result['fighter_name']}: {image_count} images | {result['status']}")

    print("-" * 70)
    print(f"Found: {found_count}/{len(fighters)} fighters")
    print(f"Not found: {not_found}/{len(fighters)} fighters")
    print("\n✓ All done! Check data/fighter_photos.json for results.")


if __name__ == "__main__":
    main()