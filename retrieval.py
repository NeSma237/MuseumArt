from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

db = FAISS.load_local(
    r"D:\ArtMuse\data\vector_db",
    embeddings,
    allow_dangerous_deserialization=True
)

retriever = db.as_retriever(
    search_kwargs={"k": 1}
)

def retrieve_context(artwork_name):
    docs = retriever.invoke(artwork_name)

    if len(docs) == 0:
        return None

    return docs[0]