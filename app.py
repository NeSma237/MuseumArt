import io
import re
import time
import hashlib
import tempfile
import requests
import streamlit as st

from identifier import identify_artwork
from retrieval import retrieve_context

# optional: similar-artworks needs a helper in identifier.py we may not have yet
try:
    from identifier import find_similar_artworks
except ImportError:
    find_similar_artworks = None

# optional: voice features need two extra packages
try:
    import speech_recognition as sr
    VOICE_INPUT_AVAILABLE = True
except ImportError:
    VOICE_INPUT_AVAILABLE = False

try:
    from gtts import gTTS
    VOICE_OUTPUT_AVAILABLE = True
except ImportError:
    VOICE_OUTPUT_AVAILABLE = False

# ==========================================================
# Config
# ==========================================================

API_URL = "https://tidal-easily-diligence.ngrok-free.dev/generate"

HEADERS = {
    "Authorization": "Bearer secret123"
}

st.set_page_config(
    page_title="European Paintings | AI Docent",
    page_icon="🖼️",
    layout="wide"
)

# ==========================================================
# Palettes — light (day gallery) / dark (evening gallery)
# ==========================================================

PALETTE_LIGHT = {
    "--wall": "#4B1E22",
    "--wall-deep": "#350F13",
    "--gold": "#B58B4E",
    "--gold-light": "#D9B97C",
    "--btn-gold": "#C89B3C",
    "--btn-gold-hover": "#B48729",
    "--ivory": "#F5EFE1",
    "--ivory-deep": "#EDE3CC",
    "--ink": "#241B16",
    "--stone": "#8A7F6E",
    "--green": "#5B6B4F",
    "--card-bg": "#FFFFFF",
}

PALETTE_DARK = {
    "--wall": "#2A0E11",
    "--wall-deep": "#170608",
    "--gold": "#C9A468",
    "--gold-light": "#E2C48E",
    "--btn-gold": "#D4AF6A",
    "--btn-gold-hover": "#C89B3C",
    "--ivory": "#1E1A17",
    "--ivory-deep": "#2A231F",
    "--ink": "#EDE6DA",
    "--stone": "#B8AE9F",
    "--green": "#7C9A6B",
    "--card-bg": "#26201C",
}


def build_root_css(dark):
    palette = PALETTE_DARK if dark else PALETTE_LIGHT
    body = "\n".join(f"    {k}: {v};" for k, v in palette.items())
    return f":root{{\n{body}\n}}"


if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

with open("style.css") as f:
    style_body = f.read()

st.markdown(
    f"<style>{build_root_css(st.session_state.dark_mode)}\n{style_body}</style>",
    unsafe_allow_html=True
)

# ==========================================================
# Icons (single-color line art, not emoji)
# ==========================================================

ICON_ARTIST = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 3a9 9 0 1 0 0 18c1.4 0 2-.8 2-1.8 0-.6-.3-1.1-.7-1.6-.4-.5-.2-1.4.6-1.4h2A4 4 0 0 0 20 12c0-5-3.6-9-8-9z"/>'
    '<circle cx="8.3" cy="10.2" r=".9"/><circle cx="11.6" cy="7.8" r=".9"/><circle cx="15.2" cy="10.2" r=".9"/>'
    '</svg>'
)

ICON_YEAR = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3.5" y="5.5" width="17" height="15" rx="1.2"/>'
    '<path d="M3.5 9.8h17"/><path d="M8 3.5v3.2M16 3.5v3.2"/>'
    '</svg>'
)

ICON_DEPARTMENT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 9.5 12 4l9 5.5"/>'
    '<path d="M4.5 9.8v9.2M8.3 9.8v9.2M12 9.8v9.2M15.7 9.8v9.2M19.5 9.8v9.2"/>'
    '<path d="M3 19.5h18"/>'
    '</svg>'
)

# ==========================================================
# Helpers
# ==========================================================

STAGES = ["upload", "clip", "faiss", "docent"]

STAGE_META = {
    "upload": ("Room I", "Present the Work"),
    "clip":   ("Room II", "Identification — CLIP"),
    "faiss":  ("Room III", "Curatorial Archive — FAISS"),
    "docent": ("Room IV", "The Docent — Mistral 7B"),
}

CONTEXT_KEYS = [
    "Artwork Name", "Artist", "Year", "Style",
    "Department", "Materials", "Story", "Symbols", "Artist Biography"
]


def render_gallery_map(current_stage=None, done_stages=None):
    """Renders the sidebar's Room I-IV checklist with live ✔ / ⏳ / ○ state."""

    done_stages = done_stages or set()
    rows = []

    for key in STAGES:
        num, label = STAGE_META[key]

        if key in done_stages:
            icon, css_class = "✔", "done"
        elif key == current_stage:
            icon, css_class = "⏳", "running"
        else:
            icon, css_class = "○", "pending"

        rows.append(
            f'<div class="gallery-room {css_class}">'
            f'<div class="num">{icon} &nbsp;{num}</div>'
            f'<div class="label">{label}</div>'
            f'</div>'
        )

    return f'<div class="gallery-map">{"".join(rows)}</div>'


def parse_context(text):
    """Splits the RAG context (Artwork Name / Story / Symbols / ...) into a dict."""

    if not text:
        return {}

    keys_pattern = "|".join(re.escape(k) for k in CONTEXT_KEYS)
    pattern = rf"({keys_pattern}):\s*(.*?)(?=\n(?:{keys_pattern}):|\Z)"
    matches = re.findall(pattern, text, flags=re.DOTALL)

    return {k.strip(): v.strip() for k, v in matches}


def format_confidence(artwork):
    """Formats an optional 'confidence' field returned by identify_artwork()."""

    if not artwork:
        return None

    val = artwork.get("confidence")

    if val is None:
        return None

    try:
        val = float(val)
    except (TypeError, ValueError):
        return None

    if val <= 1:
        val *= 100

    return f"{val:.2f}%"


def build_suggestions(parsed_context, artwork):
    """A short list of one-tap questions, tailored to whatever context we retrieved."""

    suggestions = []

    if parsed_context.get("Symbols"):
        suggestions.append("What do the symbols in this painting mean?")
    if parsed_context.get("Story"):
        suggestions.append("Tell me the story behind this painting.")
    if parsed_context.get("Artist Biography") and artwork:
        suggestions.append(f"Tell me more about {artwork['artist']}.")
    suggestions.append("Why is this painting significant?")

    return suggestions[:4]


def detect_lang(text):
    return "ar" if re.search(r"[\u0600-\u06FF]", text or "") else "en"


def transcribe_audio(audio_bytes):
    """Speech-to-text using SpeechRecognition + Google's free web API."""

    if not VOICE_INPUT_AVAILABLE:
        return None

    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
    except Exception as e:
        st.warning(f"تعذّرت قراءة التسجيل الصوتي: {e}")
        return None

    for lang in ("ar-EG", "en-US"):
        try:
            return recognizer.recognize_google(audio_data, language=lang)
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            st.warning(f"تعذّر الوصول لخدمة التعرف على الصوت: {e}")
            return None

    st.warning("لم أتمكن من فهم الصوت المسجَّل، حاول التسجيل مرة أخرى بوضوح أكتر.")
    return None


def synthesize_speech(text):
    """Text-to-speech using gTTS. Returns mp3 bytes, or None on failure."""

    if not VOICE_OUTPUT_AVAILABLE:
        return None

    clean_text = re.sub(r"<[^<]+?>", "", text or "")

    try:
        tts = gTTS(text=clean_text, lang=detect_lang(clean_text))
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        st.warning(f"تعذّر توليد الصوت: {e}")
        return None


def handle_question(question, doc, room_slot):
    """Sends one turn to the docent, carrying prior turns along as conversation memory."""

    st.session_state.chat_history.append({"role": "user", "content": question})

    stage_line = st.empty()
    stage_line.markdown('<div class="pipeline-line">🎨 Consulting ArtMuse...</div>', unsafe_allow_html=True)
    room_slot.markdown(
        render_gallery_map("docent", st.session_state.done_stages),
        unsafe_allow_html=True
    )

    prior_turns = st.session_state.chat_history[:-1]
    conversation_so_far = "\n".join(
        f'{"Visitor" if m["role"] == "user" else "Docent"}: {m["content"]}'
        for m in prior_turns
    )
    full_question = f"{conversation_so_far}\nVisitor: {question}" if conversation_so_far else question

    try:
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json={"context": doc.page_content, "question": full_question}
        )
    except requests.RequestException as e:
        stage_line.empty()
        st.error(f"تعذّر الوصول إلى الخادم: {e}")
        return

    stage_line.markdown('<div class="pipeline-line">✍️ Writing response...</div>', unsafe_allow_html=True)
    time.sleep(0.3)
    stage_line.empty()

    if response.status_code != 200:
        st.error("The docent could not be reached.")
        return

    data = response.json()
    answer = data.get("answer", data)

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.session_state.done_stages.add("docent")
    room_slot.markdown(
        render_gallery_map(None, st.session_state.done_stages),
        unsafe_allow_html=True
    )


# ==========================================================
# Session state
# ==========================================================

if "done_stages" not in st.session_state:
    st.session_state.done_stages = set()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if "audio_cache" not in st.session_state:
    st.session_state.audio_cache = {}

if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

# ==========================================================
# Sidebar — the gallery map
# ==========================================================

with st.sidebar:

    st.markdown(
        """
<div class="eyebrow">The Metropolitan Museum of Art</div>
<h1 style="margin-top:.2rem;">European Paintings</h1>
""",
        unsafe_allow_html=True
    )

    st.markdown('<div class="divider-gold"></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow eyebrow-gold">Gallery Map</div>', unsafe_allow_html=True)

    room_slot = st.empty()
    room_slot.markdown(
        render_gallery_map(done_stages=st.session_state.done_stages),
        unsafe_allow_html=True
    )

    st.markdown('<div class="divider-gold"></div>', unsafe_allow_html=True)
    st.markdown('<span class="status-pill">● Galleries Open</span>', unsafe_allow_html=True)

# ==========================================================
# Top bar — dark mode toggle
# ==========================================================

top_left, top_right = st.columns([9, 1])

with top_right:
    toggle_label = "🌞" if st.session_state.dark_mode else "🌙"
    if st.button(toggle_label, key="theme_toggle", type="secondary", help="Toggle day / night gallery lighting"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# ==========================================================
# Masthead
# ==========================================================

st.markdown(
    """
<div class="met-masthead">
  <div class="eyebrow">Department of European Paintings</div>
  <h1>An AI Docent for the Galleries</h1>
  <p>Present a work. It will be identified, researched, and discussed.</p>
</div>
""",
    unsafe_allow_html=True
)

doc = None
artwork = None
parsed_context = {}

# ==========================================================
# Room I — upload (full width, quiet)
# ==========================================================

st.markdown(
    '<div class="eyebrow eyebrow-gold" style="text-align:center;">Room I &nbsp;·&nbsp; Present the Work</div>',
    unsafe_allow_html=True
)
st.write("")

uploaded_file = st.file_uploader(
    "Upload a photograph of the painting",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed"
)

# ==========================================================
# Once a work is presented: hero image, identification, archive
# ==========================================================

if uploaded_file is not None:

    st.session_state.done_stages.add("upload")
    room_slot.markdown(
        render_gallery_map("clip", st.session_state.done_stages),
        unsafe_allow_html=True
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(uploaded_file.read())
        image_path = tmp.name

    st.write("")

    with st.spinner("🔎 Identifying artwork..."):
        artwork = identify_artwork(image_path)

    if artwork is None:

        st.error("This work could not be identified in the collection.")

    else:

        st.session_state.done_stages.add("clip")
        room_slot.markdown(
            render_gallery_map("faiss", st.session_state.done_stages),
            unsafe_allow_html=True
        )

        # ---------- Hero image ----------

        st.image(uploaded_file, use_container_width=True)

        confidence = format_confidence(artwork)

        if confidence:
            st.markdown(
                f"""
<div class="confidence-badge">
  <span class="eyebrow-gold">Artwork Identified</span>
  <span class="confidence-value">{confidence}</span>
  <span class="eyebrow">Confidence</span>
</div>
""",
                unsafe_allow_html=True
            )

        with st.spinner("🧠 Searching Museum Archive..."):
            doc = retrieve_context(artwork["name"])

        st.session_state.done_stages.add("faiss")
        room_slot.markdown(
            render_gallery_map(None, st.session_state.done_stages),
            unsafe_allow_html=True
        )

        parsed_context = parse_context(doc.page_content) if doc else {}

        # ==================================================
        # Two columns: Artwork Profile  |  Ask the Docent
        # ==================================================

        left, right = st.columns([1, 1], gap="large")

        # ---------- LEFT: magazine-style artwork profile ----------

        with left:

            st.markdown('<div class="eyebrow eyebrow-gold">Artwork Profile</div>', unsafe_allow_html=True)

            title = parsed_context.get("Artwork Name", artwork["name"])

            st.markdown(
                f"""
<div class="plaque">
  <div class="plaque-title">{title}</div>
  <div class="plaque-sub">{artwork["artist"]}, {artwork["year"]}</div>
  <div class="meta-row">
    <div class="meta-item">
      <span class="meta-icon">{ICON_ARTIST}</span>
      <div class="meta-text">
        <div class="eyebrow">Artist</div>
        <div class="value">{artwork["artist"]}</div>
      </div>
    </div>
    <div class="meta-item">
      <span class="meta-icon">{ICON_YEAR}</span>
      <div class="meta-text">
        <div class="eyebrow">Year</div>
        <div class="value">{artwork["year"]}</div>
      </div>
    </div>
    <div class="meta-item">
      <span class="meta-icon">{ICON_DEPARTMENT}</span>
      <div class="meta-text">
        <div class="eyebrow">Department</div>
        <div class="value">{artwork["department"]}</div>
      </div>
    </div>
  </div>
</div>
""",
                unsafe_allow_html=True
            )

            if parsed_context.get("Story"):
                st.markdown(
                    f"""
<div class="magazine-section">
  <div class="eyebrow eyebrow-gold">The Story</div>
  <p class="magazine-body">{parsed_context["Story"]}</p>
</div>
""",
                    unsafe_allow_html=True
                )

            if parsed_context.get("Symbols"):
                st.markdown(
                    f"""
<div class="magazine-section">
  <div class="eyebrow eyebrow-gold">Historical Context</div>
  <p class="magazine-body">{parsed_context["Symbols"]}</p>
</div>
""",
                    unsafe_allow_html=True
                )

            if parsed_context.get("Artist Biography"):
                st.markdown(
                    f"""
<div class="magazine-section">
  <div class="eyebrow eyebrow-gold">Interesting Facts</div>
  <p class="magazine-body">{parsed_context["Artist Biography"]}</p>
</div>
""",
                    unsafe_allow_html=True
                )

            # ---------- Similar Artworks (CLIP embeddings) ----------

            st.markdown('<div class="divider-gold"></div>', unsafe_allow_html=True)
            st.markdown('<div class="eyebrow eyebrow-gold">Similar Artworks</div>', unsafe_allow_html=True)

            if find_similar_artworks is None:
                st.caption(
                    "يحتاج هذا القسم إلى دالة `find_similar_artworks(image_path, top_k)` "
                    "داخل identifier.py ترجع أقرب اللوحات بالـ CLIP embeddings."
                )
            else:
                with st.spinner("🎨 Finding similar artworks..."):
                    try:
                        similar = find_similar_artworks(image_path, top_k=4)
                    except Exception as e:
                        similar = []
                        st.caption(f"تعذّر جلب اللوحات المشابهة: {e}")

                if similar:
                    sim_cols = st.columns(len(similar))
                    for sim_col, item in zip(sim_cols, similar):
                        with sim_col:
                            if item.get("image_path"):
                                st.image(item["image_path"], use_container_width=True)
                            st.markdown(
                                f'<div class="similar-caption">{item.get("name", "")}'
                                f'<span class="eyebrow">{item.get("artist", "")}</span></div>',
                                unsafe_allow_html=True
                            )

            st.markdown('<div class="divider-gold"></div>', unsafe_allow_html=True)

            dev_mode = st.checkbox("Developer Mode")

            if dev_mode:
                with st.expander("Raw Retrieved Context (RAG)"):
                    st.text(doc.page_content if doc else "No context available.")

        # ---------- RIGHT: Ask the Docent (conversation mode) ----------

        with right:

            st.markdown('<div class="eyebrow eyebrow-gold">Room IV &nbsp;·&nbsp; The Docent</div>', unsafe_allow_html=True)
            st.markdown("### Ask the Docent")

            # Suggested questions
            suggestions = build_suggestions(parsed_context, artwork)
            st.markdown('<div class="eyebrow" style="margin-bottom:.5rem;">Suggested Questions</div>', unsafe_allow_html=True)
            sugg_cols = st.columns(len(suggestions))
            for sc, suggestion in zip(sugg_cols, suggestions):
                with sc:
                    if st.button(suggestion, key=f"sugg_{suggestion}", type="secondary", use_container_width=True):
                        st.session_state.pending_question = suggestion

            st.write("")

            # Chat history
            for i, msg in enumerate(st.session_state.chat_history):
                avatar = "🧠" if msg["role"] == "assistant" else "🙋"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

                    if msg["role"] == "assistant" and VOICE_OUTPUT_AVAILABLE:
                        if st.button("🔊 Speak", key=f"speak_{i}", type="secondary"):
                            audio_bytes = st.session_state.audio_cache.get(i)
                            if audio_bytes is None:
                                with st.spinner("🔊 Synthesizing voice..."):
                                    audio_bytes = synthesize_speech(msg["content"])
                                st.session_state.audio_cache[i] = audio_bytes
                            if audio_bytes:
                                st.audio(audio_bytes, format="audio/mp3")

            # Voice input
            voice_question = None

            if VOICE_INPUT_AVAILABLE:
                audio_value = st.audio_input("🎙️ Or ask by voice")
                if audio_value is not None:
                    audio_bytes = audio_value.getvalue()
                    audio_hash = hashlib.md5(audio_bytes).hexdigest()
                    if st.session_state.last_audio_hash != audio_hash:
                        st.session_state.last_audio_hash = audio_hash
                        with st.spinner("🎙️ Transcribing..."):
                            voice_question = transcribe_audio(audio_bytes)
            else:
                st.caption("للتفعيل: `pip install SpeechRecognition` عشان يظهر إدخال الصوت.")

            # Typed input (pinned at the bottom by Streamlit automatically)
            typed_question = st.chat_input("Ask the docent anything about this work...")

            question_to_send = st.session_state.pending_question or voice_question or typed_question

            if question_to_send:
                st.session_state.pending_question = None
                handle_question(question_to_send, doc, room_slot)
                st.rerun()

            if not VOICE_OUTPUT_AVAILABLE:
                st.caption("للتفعيل: `pip install gTTS` عشان يظهر زر 🔊 Speak تحت كل إجابة.")