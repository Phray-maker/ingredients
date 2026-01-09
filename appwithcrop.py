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

# --- TESSERACT CONFIGURATION ---
# On Streamlit Cloud, Tesseract is found in the system path via packages.txt
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")


# --- UTILITY: BASE64 CONVERSION ---
def get_image_base64(img):
    """Encodes PIL image to Base64 to bypass cloud URL resolution issues."""
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


# Initialize session state for the text area
if 'verified_text' not in st.session_state:
    st.session_state['verified_text'] = ""

st.title("🔬 Interactive Chemical Scanner")

uploaded_file = st.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 1. LOAD & RESIZE
    img = Image.open(uploaded_file).convert('RGB')

    # RESIZER: Caps resolution at 1800px to keep Base64 strings manageable
    MAX_SIZE = 1800
    if max(img.size) > MAX_SIZE:
        img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

    # Calculate scale for coordinate mapping
    w, h = img.size
    display_width = 700
    scale = display_width / w
    display_height = int(h * scale)

    # Convert the resized image to Base64 for the canvas background
    img_base64 = get_image_base64(img)

    col_canvas, col_text = st.columns([1.5, 1])

    with col_canvas:
        st.subheader("Step 1: Select Area")
        # background_image=img_base64 is the primary fix for the blank canvas
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#ff8c00",
            background_image=img_base64,
            update_streamlit=True,
            height=display_height,
            width=display_width,
            drawing_mode="rect",
            key="canvas",
        )

    with col_text:
        st.subheader("Step 2: Read & Verify")

        if st.button("Run OCR on Selection 🔍"):
            ocr_input_img = img

            # Extract coordinates from canvas and map back to high-res image
            if canvas_result.json_data and len(canvas_result.json_data["objects"]) > 0:
                obj = canvas_result.json_data["objects"][-1]

                # Use .get() to safely retrieve coords
                left = int(obj.get("left", 0) / scale)
                top = int(obj.get("top", 0) / scale)
                width = int((obj.get("width", 0) * obj.get("scaleX", 1)) / scale)
                height = int((obj.get("height", 0) * obj.get("scaleY", 1)) / scale)

                # Perform the crop on the original high-res PIL object
                ocr_input_img = img.crop((left, top, left + width, top + height))

            with st.spinner("Processing text..."):
                # PSM 6: Assume a single uniform block of text
                raw_text = pytesseract.image_to_string(ocr_input_img, config='--oem 3 --psm 6')

                # Search for 'Ingredients' header within the selection
                clean_match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', raw_text, re.DOTALL)
                st.session_state['verified_text'] = clean_match.group(1) if clean_match else raw_text

        # User-editable area for manual typo correction
        user_text = st.text_area("Verify Ingredients:", value=st.session_state['verified_text'], height=250)
        st.session_state['verified_text'] = user_text

        if st.button("Check PubChem 🚀"):
            st.divider()
            # Split items by comma or newline
            items = [i.strip() for i in re.split(r'[,\n]', user_text) if len(i.strip()) > 2]

            res_cols = st.columns(2)
            for idx, item in enumerate(items):
                # Sanitize name for API search
                search_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', item).strip()

                with res_cols[idx % 2]:
                    try:
                        results = pcp.get_compounds(search_name, 'name')
                        if results:
                            c = results[0]
                            st.success(f"**{item}**")
                            # Display molecular PNG from PubChem
                            st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{c.cid}/record/PNG")
                        else:
                            st.info(f"**{item}** (Not found)")
                    except Exception:
                        st.error(f"Error searching {item}")