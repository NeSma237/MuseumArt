"""
ArtMuse AI
Step 1: Collect Artwork IDs from Metropolitan Museum API

This script:
- Searches using multiple keywords
- Removes duplicate IDs
- Saves all IDs into data/ids.json
"""

import json
import os
import time
import requests

# =====================================================
# Configuration
# =====================================================

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"

DATA_DIR = "data"
IDS_FILE = os.path.join(DATA_DIR, "ids.json")

os.makedirs(DATA_DIR, exist_ok=True)

SEARCH_TERMS = [

    # General
    "painting",
    "art",
    "portrait",
    "landscape",
    "still life",

    # Subjects
    "woman",
    "man",
    "child",
    "family",
    "horse",
    "dog",
    "cat",
    "flower",
    "tree",
    "forest",
    "river",
    "sea",
    "boat",
    "castle",
    "church",
    "garden",
    "city",
    "village",

    # History
    "religion",
    "mythology",
    "battle",
    "king",
    "queen",
    "angel",
    "saint",

    # Styles
    "renaissance",
    "baroque",
    "impressionism",
    "expressionism",
    "cubism",

    # Nature
    "nature",
    "sun",
    "moon",
    "night",

    # Objects
    "music",
    "book",
    "window",
    "table",
    "chair"

]

# =====================================================
# Collect IDs
# =====================================================

all_ids = set()

print("=" * 60)
print("Collecting Artwork IDs...")
print("=" * 60)

for keyword in SEARCH_TERMS:

    print(f"Searching: {keyword}")

    try:

        response = requests.get(
            f"{BASE_URL}/search",
            params={
                "q": keyword,
                "hasImages": True
            },
            timeout=30
        )

        response.raise_for_status()

        ids = response.json().get("objectIDs", [])

        if ids:

            before = len(all_ids)

            all_ids.update(ids)

            added = len(all_ids) - before

            print(f"   + {added} new IDs")

        else:

            print("   + 0 IDs")

    except Exception as e:

        print(e)

    time.sleep(0.3)

# =====================================================
# Save
# =====================================================

all_ids = sorted(list(all_ids))

with open(IDS_FILE, "w") as f:
    json.dump(all_ids, f)

print("\n" + "=" * 60)
print("Finished")
print("=" * 60)

print(f"Total Unique IDs: {len(all_ids):,}")

print(f"Saved to: {IDS_FILE}")