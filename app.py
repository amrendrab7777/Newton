import streamlit as st
import groq
import base64
from duckduckgo_search import DDGS
from PyPDF2 import PdfReader
import docx

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Newton", page_icon="🤖", layout="centered")

# --- 2. SECURE API LOADING ---
try:
    API_KEY = st.secrets["GROQ_API_KEY"]
    client = groq.Groq(api_key=API_KEY)
except Exception:
    st.error("⚠️ Developer Setup Required: Add 'GROQ_API_KEY' to Streamlit Secrets.")
    st.stop()

# --- 3. FILE PROCESSING UTILITIES ---
def extract_text(uploaded_file):
    """Reads text from PDF and DOCX files."""
    text = ""
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text()
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_file)
        text = "\n".join([para.text for para in doc.paragraphs])
    return text

def encode_image(uploaded_file):
    """Converts image to base64 for the Vision model."""
    return base64.b64encode(uploaded_file.read()).decode('utf-8')

# --- 4. WEB SEARCH ENGINE ---
def get_web_context(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=2)]
            return "\n".join(results)
    except:
        return ""

# --- 5. Newton UI ---
st.title("🤖 I am Newton")
st.caption("Now supporting Images, PDFs, and Web Search")

# Sidebar for File Uploads
with st.sidebar:
    st.header("📁 Upload Files")
    uploaded_file = st.file_uploader("Upload Image, PDF, or Doc", type=["pdf", "docx", "jpg", "jpeg", "png"])
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. CHAT LOGIC ---
if prompt := st.chat_input("Ask Newton about your file or the web..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        file_context = ""
        is_image = False
        
        # Check if a file is uploaded
        if uploaded_file:
            if uploaded_file.type.startswith("image"):
                is_image = True
                base64_image = encode_image(uploaded_file)
            else:
                with st.spinner("Newton is reading your document..."):
                    file_context = extract_text(uploaded_file)

        # Build the Prompt
        with st.status("🔍 Analyzing...", expanded=False):
            web_info = get_web_context(prompt)
            
        full_prompt = f"File Content: {file_context}\n\nWeb Content: {web_info}\n\nUser Question: {prompt}"
        
        response_placeholder = st.empty()
        full_response = ""

        try:
            # If it's an image, use the Vision Model. Otherwise, use the standard Llama model.
            model_to_use = "llama-3.2-11b-vision-preview" if is_image else "llama-3.3-70b-versatile"
            
            # Prepare messages
            messages = []
            if is_image:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                })
            else:
                messages.append({"role": "user", "content": full_prompt})

            stream = client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
        except Exception as e:
            st.error(f"Newton error: {str(e)}")


    st.session_state.messages.append({"role": "assistant", "content": full_response})
