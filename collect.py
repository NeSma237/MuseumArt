
import os
import json
import random
import time
import requests
 
# ==========================
# Configuration
# ==========================
 
NUM_ARTWORKS = 500
 
DEPARTMENT_FILTER = "European Paintings"   # <-- الفلتر الجديد: نقبل بس اللوحات من القسم ده
 
BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
 
DATA_DIR = "data"
 
IDS_FILE = os.path.join(DATA_DIR, "ids.json")
 
ARTWORKS_FILE = os.path.join(DATA_DIR, "artworks.json")
 
IMAGES_DIR = os.path.join(DATA_DIR, "imagesss")
 
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
 
print(f"Trying to collect {NUM_ARTWORKS} artworks from '{DEPARTMENT_FILTER}'...\n")
 
checked = 0
 
for obj_id in object_ids:
 
    if len(artworks) >= NUM_ARTWORKS:
        break
 
    checked += 1
 
    try:
 
        response = requests.get(
            f"{BASE_URL}/objects/{obj_id}",
            timeout=20
        )
 
        response.raise_for_status()
 
        data = response.json()
 
    except:
 
        continue
 
    # ==========================
    # فلتر القسم - أول حاجة نتأكد منها قبل أي حاجة تانية
    # ==========================
 
    department = data.get("department", "")
 
    if department != DEPARTMENT_FILTER:
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
 
        "department": department,
 
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
 
    # طباعة تقدم كل 200 محاولة، عشان تعرفي إن السكريبت شغال ومش واقف
    if checked % 200 == 0:
        print(f"  ... checked {checked} objects so far, found {len(artworks)} matching '{DEPARTMENT_FILTER}'")
 
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
 
print(f"Checked {checked} objects total.")
 
print(f"Collected {len(artworks)} artworks from '{DEPARTMENT_FILTER}'.")
 
print(f"Saved to {ARTWORKS_FILE}")
 
