from identifier import identify_artwork
from retrieval import retrieve_context

image = r"D:\ArtMuse\data\imagesss\435621.jpg"

artwork = identify_artwork(image)

print("Artwork:")
print(artwork["name"])

print("-" * 60)

doc = retrieve_context(artwork["name"])

print(doc.page_content)