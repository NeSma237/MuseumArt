import os
import json
import random
import time
import requests

# ==========================
# Configuration
# ==========================

NUM_ARTWORKS = 500

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"

DATA_DIR = "data"

IDS_FILE = os.path.join(DATA_DIR, "ids.json")

ARTWORKS_FILE = os.path.join(DATA_DIR, "artworks.json")

IMAGES_DIR = os.path.join(DATA_DIR, "images")

os.makedirs(IMAGES_DIR, exist_ok=True)

# ==========================
# Load IDs
# ==========================

with open(IDS_FILE, "r") as f:
    object_ids = json.load(f)

random.shuffle(object_ids)

artworks = []

# ==========================
# Download
# ==========================

print(f"Trying to collect {NUM_ARTWORKS} artworks...\n")

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

    except:

        continue

    title = data.get("title")

    artist = data.get("artistDisplayName")

    year = data.get("objectDate")

    medium = data.get("medium")

    image_url = data.get("primaryImage")

    object_url = data.get("objectURL")

    if (
        not title
        or not artist
        or not year
        or not medium
        or not image_url
    ):
        continue

    # ==========================
    # Download Image
    # ==========================

    image_filename = f"{obj_id}.jpg"

    image_path = os.path.join(
        IMAGES_DIR,
        image_filename
    )

    try:

        img = requests.get(
            image_url,
            timeout=20
        )

        img.raise_for_status()

        with open(image_path, "wb") as f:

            f.write(img.content)

    except:

        continue

    # ==========================
    # Save Metadata
    # ==========================

    artwork = {

        "id": obj_id,

        "name": title,

        "artist": artist,

        "year": year,

        "style": data.get("classification", ""),

        "culture": data.get("culture", ""),

        "materials": medium,

        "department": data.get("department", ""),

        "dimensions": data.get("dimensions", ""),

        "repository": data.get("repository", ""),

        "object_url": object_url,

        "image_file": image_filename,

        "image_url": image_url,

        "story": "",

        "symbols": "",

        "artist_bio": "",

        "historical_context": "",

        "interesting_facts": []

    }

    artworks.append(artwork)

    print(
        f"[{len(artworks)}/{NUM_ARTWORKS}]",
        title,
        "-",
        artist
    )

    time.sleep(0.1)

# ==========================
# Save JSON
# ==========================

with open(
    ARTWORKS_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        artworks,
        f,
        ensure_ascii=False,
        indent=4
    )

print("\nDone!")

print(f"Collected {len(artworks)} artworks.")

print(f"Saved to {ARTWORKS_FILE}")