from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# نفس موديل الـ Embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# تحميل قاعدة البيانات
db = FAISS.load_local(
    r"D:\ArtMuse\data\vector_db",
    embeddings,
    allow_dangerous_deserialization=True
)

retriever = db.as_retriever(
    search_kwargs={"k": 1}
)

# جربي سؤال
query = "Tell me about The 'A Woman Reading'"

docs = retriever.invoke(query)

print("=" * 80)
print(docs[0].page_content)
print("=" * 80)
print(docs[0].metadata)