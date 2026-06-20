#!/usr/bin/env python3
"""
Fighter Photos Organizer
Sorts fighter photo URLs into correct categories based on image type.
- Headshots: URLs without 'athlete_bio_full_body' in path
- Body shots/profiles: URLs with 'athlete_bio_full_body' in path

Run this once to clean up your fighter_photos.json
"""

import json
from pathlib import Path

# Get the project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PHOTOS_FILE = DATA_DIR / "fighter_photos.json"


def categorize_images(images: list) -> tuple[str, list]:
    """
    Categorize images into headshot and body shots.

    Returns: (best_headshot_url, [other_images])

    Logic:
    - Headshots: URLs without 'athlete_bio_full_body' style indicator
    - Body shots: URLs with 'athlete_bio_full_body' in the path
    """
    headshots = []
    body_shots = []

    for img_url in images:
        if "athlete_bio_full_body" in img_url.lower():
            body_shots.append(img_url)
        else:
            headshots.append(img_url)

    # Use first headshot as primary, or first image if no headshots found
    primary_headshot = headshots[0] if headshots else (body_shots[0] if body_shots else None)

    # All other images go to profile_images
    other_images = []
    if headshots:
        other_images.extend(headshots[1:])  # Remaining headshots
    other_images.extend(body_shots)  # All body shots

    return primary_headshot, other_images


def organize_photos():
    """Read, organize, and save fighter photos."""

    if not PHOTOS_FILE.exists():
        print(f"❌ File not found: {PHOTOS_FILE}")
        return

    print("=" * 70)
    print("Fighter Photos Organizer")
    print("=" * 70)
    print(f"Reading from: {PHOTOS_FILE}\n")

    # Load photos
    with open(PHOTOS_FILE, 'r', encoding='utf-8') as f:
        fighters = json.load(f)

    print(f"Processing {len(fighters)} fighters...\n")

    # Organize each fighter's photos
    changes_made = 0
    for fighter in fighters:
        fighter_name = fighter.get("fighter_name", "Unknown")
        images = fighter.get("images", [])

        if not images:
            print(f"⊘ {fighter_name}: No images")
            continue

        old_headshot = fighter.get("headshot")
        old_profile_count = len(fighter.get("profile_images", []))

        # Categorize images
        headshot, profile_images = categorize_images(images)

        # Update fighter data
        fighter["headshot"] = headshot
        fighter["profile_images"] = profile_images

        # Check if changes were made
        if headshot != old_headshot or len(profile_images) != old_profile_count:
            changes_made += 1
            print(f"✓ {fighter_name}")
            print(f"  Headshot: {headshot[:60]}...")
            print(f"  Profile images: {len(profile_images)}")
        else:
            print(f"  {fighter_name}: Already organized")

    print("\n" + "=" * 70)
    print(f"Changes made: {changes_made}/{len(fighters)} fighters")

    # Save organized photos
    with open(PHOTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(fighters, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved to: {PHOTOS_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    organize_photos()