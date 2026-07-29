import json
import os

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# ==========================================
# Paths
# ==========================================

DATA_DIR = r"D:\ArtMuse\data"

JSON_PATH = os.path.join(DATA_DIR, "artworks.json")

VECTOR_DB_PATH = os.path.join(DATA_DIR, "vector_db")

# ==========================================
# Load JSON
# ==========================================

with open(JSON_PATH, "r", encoding="utf-8") as f:
    artworks = json.load(f)

# ==========================================
# Convert JSON -> Documents
# ==========================================

documents = []

for art in artworks:

    interesting = art.get("interesting_facts", [])

    if isinstance(interesting, list):
        interesting = "\n".join(
            f"- {fact}" for fact in interesting
        )

    text = f"""
Artwork Name:
{art.get("name","")}

Artist:
{art.get("artist","")}

Year:
{art.get("year","")}

Style:
{art.get("style","")}

Department:
{art.get("department","")}

Materials:
{art.get("materials","")}

Story:
{art.get("story","")}

Symbols:
{art.get("symbols","")}

Artist Biography:
{art.get("artist_bio","")}

Historical Context:
{art.get("historical_context","")}

Interesting Facts:
{interesting}
"""

    doc = Document(
        page_content=text,
        metadata={
            "id": art.get("id"),
            "name": art.get("name"),
            "artist": art.get("artist"),
            "image_file": art.get("image_file"),
            "object_url": art.get("object_url")
        }
    )

    documents.append(doc)

print(f"Documents created: {len(documents)}")

# ==========================================
# Split Documents
# ==========================================

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

split_documents = splitter.split_documents(documents)

print(f"Chunks: {len(split_documents)}")

# ==========================================
# Embedding Model
# ==========================================

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# ==========================================
# Build FAISS
# ==========================================

vector_db = FAISS.from_documents(
    split_documents,
    embeddings
)

vector_db.save_local(VECTOR_DB_PATH)

print("Vector Database created successfully!")

print(VECTOR_DB_PATH)