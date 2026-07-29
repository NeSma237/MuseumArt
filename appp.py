import requests
import tempfile
import streamlit as st

from identifier import identify_artwork
from retrieval import retrieve_context

# ======================================
# Page Config
# ======================================

st.set_page_config(
    page_title="ArtMuse AI",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ======================================
# CSS
# ======================================

st.markdown("""
<style>

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

.stApp{
    background:#f7f2ea;
}

.block-container{
    padding-top:2rem;
    padding-bottom:2rem;
    max-width:1300px;
}

.hero{
    background:linear-gradient(135deg,#e8dcc6,#d6c2a3);
    border-radius:25px;
    padding:35px;
    text-align:center;
    margin-bottom:35px;
    box-shadow:0 15px 40px rgba(0,0,0,.15);
}

.hero h1{
    color:#6d4c1f;
    font-size:48px;
    margin-bottom:8px;
}

.hero p{
    color:#5d4b2d;
    font-size:20px;
}

.card{
    background:white;
    border-radius:22px;
    padding:25px;
    box-shadow:0 12px 30px rgba(0,0,0,.08);
    border:1px solid rgba(180,150,90,.2);
    margin-bottom:20px;
}

.info-card{
    background:white;
    border-left:6px solid #b68d40;
    border-radius:15px;
    padding:15px;
    margin-bottom:15px;
    box-shadow:0 5px 15px rgba(0,0,0,.05);
}

.info-title{
    color:#8a6a2f;
    font-size:14px;
    font-weight:bold;
}

.info-value{
    font-size:20px;
    color:#222;
}

.answer-box{
    background:#fffdf8;
    border-left:8px solid #b68d40;
    padding:25px;
    border-radius:20px;
    box-shadow:0 10px 25px rgba(0,0,0,.08);
    font-size:18px;
    line-height:1.8;
}

.question-box{
    background:white;
    border-radius:15px;
    padding:18px;
    box-shadow:0px 10px 20px rgba(0,0,0,.05);
}

.stButton>button{

    width:100%;

    background:#b68d40;

    color:white;

    border:none;

    border-radius:15px;

    font-size:18px;

    padding:15px;

    transition:.3s;
}

.stButton>button:hover{

    background:#8a6a2f;

    transform:translateY(-3px);

    box-shadow:0 10px 20px rgba(0,0,0,.2);

}

.stTextInput>div>div>input{

    background:white;

    border-radius:15px;

    border:2px solid #d8c7a2;

    font-size:17px;

    padding:12px;

}

hr{
    margin-top:35px;
    margin-bottom:35px;
}

</style>
""", unsafe_allow_html=True)

# ======================================
# Header
# ======================================

st.markdown("""
<div class="hero">

<h1>🎨 ArtMuse AI</h1>

<p>
Discover the Story Behind Every Artwork
</p>

</div>
""", unsafe_allow_html=True)

doc = None
artwork = None


uploaded_file = st.file_uploader(
    "🖼 Upload an Artwork",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".jpg"
    ) as tmp:

        tmp.write(uploaded_file.read())
        image_path = tmp.name

    with st.spinner("🎨 Identifying artwork..."):

        artwork = identify_artwork(image_path)

    if artwork is None:

        st.error("❌ Artwork not found.")

    else:

        with st.spinner("📚 Retrieving museum information..."):

            doc = retrieve_context(
                artwork["name"]
            )

        st.success("🎉 Artwork Successfully Identified")

        left, right = st.columns([1.2, 1])

        # ==========================
        # LEFT
        # ==========================

        with left:

            st.markdown("""
            <div class="card">
            <h2 style='color:#8a6a2f'>
            📖 Artwork Information
            </h2>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="info-card">
            <div class="info-title">🎨 TITLE</div>
            <div class="info-value">{artwork['name']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="info-card">
            <div class="info-title">👩‍🎨 ARTIST</div>
            <div class="info-value">{artwork['artist']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="info-card">
            <div class="info-title">📅 YEAR</div>
            <div class="info-value">{artwork['year']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="info-card">
            <div class="info-title">🏛 DEPARTMENT</div>
            <div class="info-value">{artwork['department']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # ==========================
        # RIGHT
        # ==========================

        with right:

            st.markdown("""
            <div class="card">
            <h2 style='color:#8a6a2f'>
            🖼 Artwork Preview
            </h2>
            """, unsafe_allow_html=True)

            st.image(
                image_path,
                use_container_width=True
            )

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("📚 Museum Database Context"):

            st.text(doc.page_content)

# ==================================================
# Ask ArtMuse
# ==================================================

st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("""
<div class="card">

<h2 style="color:#8a6a2f;">
💬 Ask ArtMuse
</h2>

<p style="color:#666;">
Ask anything about the selected artwork.
</p>

</div>
""", unsafe_allow_html=True)

question = st.text_input(
    "",
    placeholder="Ask about the artist, story, symbols, history..."
)

col1, col2, col3 = st.columns([1,2,1])

with col2:

    ask = st.button(
        "✨ Ask ArtMuse",
        use_container_width=True
    )

# ==================================================
# Generate
# ==================================================

if ask:

    if uploaded_file is None:

        st.warning("Please upload an artwork first.")

    elif question.strip() == "":

        st.warning("Please enter your question.")

    else:

        with st.spinner("🧠 ArtMuse is thinking..."):

            response = requests.post(
                "https://tidal-easily-diligence.ngrok-free.dev/generate",
                headers={
                    "Authorization":"Bearer secret123"
                },
                json={
                    "context":doc.page_content,
                    "question":question
                }
            )

        if response.status_code != 200:

            st.error("API Error")

            st.json(response.json())

        else:

            data = response.json()

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("""
            <div class="card">

            <h2 style="color:#8a6a2f;">
            🤖 Museum Guide
            </h2>

            </div>
            """, unsafe_allow_html=True)

            st.markdown(
                f"""
                <div class="answer-box">

                {data["answer"]}

                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<br>", unsafe_allow_html=True)

            with st.expander("📚 View Context Sent To AI"):

                st.text(doc.page_content)
