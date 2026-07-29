import os
import json
import numpy as np
from PIL import Image
import torch
import open_clip

# ===========================
# Paths
# ===========================
DATA_DIR = r"D:\ArtMuse\data"
IMAGES_DIR = os.path.join(DATA_DIR, "imagesss")
ARTWORKS_JSON = os.path.join(DATA_DIR, "artworks.json")

EMBEDDINGS_FILE = os.path.join(DATA_DIR, "reference_embeddings.npy")
IDS_FILE = os.path.join(DATA_DIR, "reference_ids.npy")

# ===========================
# Load CLIP Model
# ===========================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using device: {DEVICE}")

model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32",
    pretrained="openai"
)

model = model.to(DEVICE)
model.eval()

# ===========================
# Load artworks metadata
# ===========================
with open(ARTWORKS_JSON, "r", encoding="utf-8") as f:
    artworks = json.load(f)

# ===========================
# Build Reference Embeddings
# ===========================
embeddings = []
ids = []

print(f"Building embeddings for {len(artworks)} artworks...")

with torch.no_grad():

    for art in artworks:

        # تأكد إن الصورة موجودة
        if "image_file" not in art:
            continue

        image_path = os.path.join(IMAGES_DIR, art["image_file"])

        if not os.path.exists(image_path):
            print(f"Image not found: {image_path}")
            continue

        try:
            image = Image.open(image_path).convert("RGB")

            image_input = preprocess(image).unsqueeze(0).to(DEVICE)

            embedding = model.encode_image(image_input)

            # Normalize
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

            embeddings.append(
                embedding.cpu().numpy().flatten()
            )

            ids.append(art["id"])

        except Exception as e:
            print(f"Error processing {image_path}")
            print(e)

embeddings = np.array(embeddings)
ids = np.array(ids)

print(f"Total embeddings: {len(embeddings)}")

# Save
np.save(EMBEDDINGS_FILE, embeddings)
np.save(IDS_FILE, ids)

print("Reference embeddings saved successfully.")

# ===========================
# Load saved embeddings
# ===========================
reference_embeddings = np.load(EMBEDDINGS_FILE)
reference_ids = np.load(IDS_FILE)

# ===========================
# Artwork Identification
# ===========================
CONFIDENCE_THRESHOLD = 0.25


def identify_artwork(
    image_path,
    model,
    preprocess,
    reference_embeddings,
    reference_ids,
):
    image = Image.open(image_path).convert("RGB")

    image_input = preprocess(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():

        query_embedding = model.encode_image(image_input)

        query_embedding = (
            query_embedding
            / query_embedding.norm(dim=-1, keepdim=True)
        )

        query_embedding = (
            query_embedding.cpu().numpy().flatten()
        )

    # Cosine Similarity
    similarities = reference_embeddings @ query_embedding

    best_idx = int(np.argmax(similarities))

    best_score = float(similarities[best_idx])

    # لو الثقة قليلة يبقى الصورة مش من الداتا
    if best_score < CONFIDENCE_THRESHOLD:
        return None, best_score

    return reference_ids[best_idx], best_score


# ===========================
# Example
# ===========================
test_image = r"D:\ArtMuse\test.jpg"

if os.path.exists(test_image):

    artwork_id, score = identify_artwork(
        test_image,
        model,
        preprocess,
        reference_embeddings,
        reference_ids,
    )

    if artwork_id is None:
        print(f"No matching artwork found. Score = {score:.3f}")
    else:
        print(f"Artwork ID: {artwork_id}")
        print(f"Similarity: {score:.3f}")