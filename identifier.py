import os
import json
import numpy as np
from PIL import Image
import torch
import open_clip

# ==========================
# Paths
# ==========================

DATA_DIR = r"D:\ArtMuse\data"

ARTWORKS_JSON = os.path.join(DATA_DIR, "artworks.json")

EMBEDDINGS_FILE = os.path.join(
    DATA_DIR,
    "reference_embeddings.npy"
)

IDS_FILE = os.path.join(
    DATA_DIR,
    "reference_ids.npy"
)

# ==========================
# Device
# ==========================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ==========================
# Load CLIP
# ==========================

model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32",
    pretrained="openai"
)

model = model.to(DEVICE)
model.eval()

# ==========================
# Load database
# ==========================

reference_embeddings = np.load(EMBEDDINGS_FILE)
reference_ids = np.load(IDS_FILE)

with open(ARTWORKS_JSON, "r", encoding="utf-8") as f:
    artworks = json.load(f)

artworks_dict = {
    art["id"]: art
    for art in artworks
}

CONFIDENCE_THRESHOLD = 0.25


def identify_artwork(image_path):

    image = Image.open(image_path).convert("RGB")

    image_input = preprocess(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():

        embedding = model.encode_image(image_input)

        embedding = embedding / embedding.norm(
            dim=-1,
            keepdim=True
        )

        embedding = embedding.cpu().numpy().flatten()

    similarities = reference_embeddings @ embedding

    best_index = int(np.argmax(similarities))

    score = float(similarities[best_index])

    if score < CONFIDENCE_THRESHOLD:
        return None

    artwork_id = int(reference_ids[best_index])

    return artworks_dict[artwork_id]