import streamlit as st
from streamlit_drawable_canvas import st_canvas
import pytesseract
from PIL import Image
import pubchempy as pcp
import re
import shutil
import numpy as np
import base64
from io import BytesIO

# --- TESSERACT CONFIG ---
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")


# --- IMAGE UTILITIES ---
def get_canvas_ready_img(img, display_width):
    """Resizes and converts image to Base64 to bypass Cloud/CORS issues."""
    w, h = img.size
    scale = display_width / w
    display_height = int(h * scale)

    # We resize here so the canvas library doesn't have to
    resized_img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)

    buffered = BytesIO()
    resized_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}", scale, display_height


if 'verified_text' not in st.session_state:
    st.session_state['verified_text'] = ""

st.title("🔬 Interactive Chemical Scanner")

uploaded_file = st.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 1. LOAD & PRE-RESIZE
    raw_img = Image.open(uploaded_file).convert('RGB')

    # Standardize display
    display_width = 700
    img_b64, scale, display_height = get_canvas_ready_img(raw_img, display_width)

    col_canvas, col_text = st.columns([1.5, 1])

    with col_canvas:
        st.subheader("Step 1: Select Area")
        # By passing the B64 string to a pre-resized image,
        # we avoid the 'int object has no attribute width' error.
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#ff8c00",
            background_image=Image.open(BytesIO(base64.b64decode(img_b64.split(",")[1]))),
            update_streamlit=True,
            height=display_height,
            width=display_width,
            drawing_mode="rect",
            key="canvas",
        )

    with col_text:
        st.subheader("Step 2: Read & Verify")

        if st.button("Run OCR on Selection 🔍"):
            ocr_input_img = raw_img
            if canvas_result.json_data and len(canvas_result.json_data["objects"]) > 0:
                obj = canvas_result.json_data["objects"][-1]
                left = int(obj.get("left", 0) / scale)
                top = int(obj.get("top", 0) / scale)
                width = int((obj.get("width", 0) * obj.get("scaleX", 1)) / scale)
                height = int((obj.get("height", 0) * obj.get("scaleY", 1)) / scale)
                # Crop high-res original
                ocr_input_img = raw_img.crop((left, top, left + width, top + height))

            with st.spinner("Processing text..."):
                raw_text = pytesseract.image_to_string(ocr_input_img, config='--oem 3 --psm 6')
                clean_match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', raw_text, re.DOTALL)
                st.session_state['verified_text'] = clean_match.group(1) if clean_match else raw_text

        user_text = st.text_area("Verify Ingredients:", value=st.session_state['verified_text'], height=250)
        st.session_state['verified_text'] = user_text

        if st.button("Check PubChem 🚀"):
            # ... (PubChem search logic remains the same) ...
            st.info("Searching PubChem...")
            items = [i.strip() for i in re.split(r'[,\n]', user_text) if len(i.strip()) > 2]
            for item in items:
                st.write(f"Searching: {item}")