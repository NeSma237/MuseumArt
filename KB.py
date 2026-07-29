"""
ArtMuse AI
Step 1 - Collect Artwork Dataset

Features
---------
✓ Multiple search queries
✓ Remove duplicate artworks
✓ Skip incomplete records
✓ Download high-quality artwork images
✓ Save metadata as JSON
✓ Ready for RAG pipeline
"""

import os
import json
import time
import random
import requests

# ==================================================
# Configuration
# ==================================================

NUM_ARTWORKS = 500

DEPARTMENT_ID = 11   # European Paintings

SEARCH_QUERIES = [
    "painting",
    "portrait",
    "landscape",
    "woman",
    "man",
    "flower",
    "tree",
    "horse",
    "sea",
    "religion",
    "mythology",
    "village",
    "city",
    "nature",
    "art"
]

OUTPUT_DIR = "artmuse_data"

IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

JSON_PATH = os.path.join(OUTPUT_DIR, "artworks.json")

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"

os.makedirs(IMAGES_DIR, exist_ok=True)

# ==================================================
# Search
# ==================================================

print("=" * 60)
print("Searching Metropolitan Museum Collection...")
print("=" * 60)

all_object_ids = set()

for query in SEARCH_QUERIES:

    print(f"Searching: {query}")

    try:

        response = requests.get(
            f"{BASE_URL}/search",
            params={
                "q": query,
                "hasImages": True,
                "departmentId": DEPARTMENT_ID
            },
            timeout=20
        )

        response.raise_for_status()

        ids = response.json().get("objectIDs", [])

        if ids:
            all_object_ids.update(ids)

    except Exception as e:

        print(f"Search Error ({query}): {e}")

print(f"\nFound {len(all_object_ids)} unique artworks.\n")

# ==================================================
# Shuffle IDs
# ==================================================

object_ids = list(all_object_ids)

random.shuffle(object_ids)

# ==================================================
# Download Artwork Data
# ==================================================

artworks = []

for obj_id in object_ids:

    if len(artworks) >= NUM_ARTWORKS:
        break

    try:

        response = requests.get(
            f"{BASE_URL}/objects/{obj_id}",
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

    except Exception as e:

        print(f"Skipping {obj_id}: {e}")

        continue

    title = data.get("title")

    image_url = data.get("primaryImage")

    artist = data.get("artistDisplayName")

    year = data.get("objectDate")

    medium = data.get("medium")

    object_url = data.get("objectURL")

    # Skip incomplete records

    if (
        not title
        or not image_url
        or not artist
        or not year
        or not medium
        or not object_url
    ):
        continue

    image_filename = f"{obj_id}.jpg"

    image_path = os.path.join(IMAGES_DIR, image_filename)

    # ==============================================
    # Download image
    # ==============================================

    try:

        img_response = requests.get(
            image_url,
            timeout=20
        )

        img_response.raise_for_status()

        with open(image_path, "wb") as f:

            f.write(img_response.content)

    except Exception as e:

        print(f"Image Error ({obj_id}): {e}")

        continue

    # Skip broken images

    if os.path.getsize(image_path) < 50000:

        os.remove(image_path)

        continue

    # ==============================================
    # Tags
    # ==============================================

    tags = []

    if data.get("tags"):

        tags = [
            tag["term"]
            for tag in data["tags"]
            if "term" in tag
        ]

    # ==============================================
    # Metadata
    # ==============================================

    artwork = {

        "id": obj_id,

        "name": title,

        "artist": artist,

        "artist_nationality": data.get("artistNationality", ""),

        "artist_begin_date": data.get("artistBeginDate", ""),

        "artist_end_date": data.get("artistEndDate", ""),

        "year": year,

        "style": data.get("classification", ""),

        "period": data.get("period", ""),

        "culture": data.get("culture", ""),

        "materials": medium,

        "department": data.get("department", ""),

        "dimensions": data.get("dimensions", ""),

        "repository": data.get("repository", ""),

        "object_url": object_url,

        "image_file": image_filename,

        "image_url": image_url,

        "tags": tags,

        # ===== سيتم توليدها لاحقاً =====

        "story": "",

        "symbols": "",

        "artist_bio": "",

        "historical_context": "",

        "interesting_facts": []

    }

    artworks.append(artwork)

    print(f"[{len(artworks):03}/{NUM_ARTWORKS}] {title}")

    time.sleep(0.15)

# ==================================================
# Save Dataset
# ==================================================

with open(JSON_PATH, "w", encoding="utf-8") as f:

    json.dump(
        artworks,
        f,
        ensure_ascii=False,
        indent=4
    )

print("\n" + "=" * 60)
print("Dataset Created Successfully")
print("=" * 60)

print(f"Collected Artworks : {len(artworks)}")

print(f"Images Folder      : {IMAGES_DIR}")

print(f"JSON File          : {JSON_PATH}")