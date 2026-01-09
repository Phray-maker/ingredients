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
# Streamlit Cloud uses the system path for Tesseract via packages.txt
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")


# --- IMAGE UTILITIES ---
def get_image_base64(img):
    """
    Converts a PIL image to a Base64 string.
    This is the 'secret sauce' for making images show up on the canvas
    in cloud environments.
    """
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


if 'verified_text' not in st.session_state:
    st.session_state['verified_text'] = ""

st.title("🔬 Interactive Chemical Scanner")

uploaded_file = st.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 2. Convert your image to the base64 string
    img_base64 = get_image_base64(img)

    # RESIZER: Limits pixels to prevent browser memory crashes
    MAX_SIZE = 1800
    if max(img.size) > MAX_SIZE:
        img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

    w, h = img.size
    display_width = 700
    scale = display_width / w
    display_height = int(h * scale)

    # Convert the image to Base64 for the canvas
    img_base64 = get_image_base64(img)

    col_canvas, col_text = st.columns([1.5, 1])

    # 3. Update the canvas call
    with col_canvas:
        st.subheader("Step 1: Select Area")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#ff8c00",
            # CHANGE: Use the base64 string here instead of the PIL object
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

            # Robust coordinate retrieval for the crop
            if canvas_result.json_data and len(canvas_result.json_data["objects"]) > 0:
                obj = canvas_result.json_data["objects"][-1]

                left = int(obj.get("left", 0) / scale)
                top = int(obj.get("top", 0) / scale)
                width = int((obj.get("width", 0) * obj.get("scaleX", 1)) / scale)
                height = int((obj.get("height", 0) * obj.get("scaleY", 1)) / scale)

                # High-res crop ensures better OCR accuracy
                ocr_input_img = img.crop((left, top, left + width, top + height))

            with st.spinner("Processing text..."):
                # PSM 6: Uniform block of text
                raw_text = pytesseract.image_to_string(ocr_input_img, config='--oem 3 --psm 6')

                # Use regex to strip the header if it exists
                clean_match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', raw_text, re.DOTALL)
                st.session_state['verified_text'] = clean_match.group(1) if clean_match else raw_text

        # The interactive edit area
        user_text = st.text_area("Verify Ingredients:", value=st.session_state['verified_text'], height=250)
        st.session_state['verified_text'] = user_text

        if st.button("Check PubChem 🚀"):
            st.divider()
            # Split items by comma or newline
            items = [i.strip() for i in re.split(r'[,\n]', user_text) if len(i.strip()) > 2]

            res_cols = st.columns(2)
            for idx, item in enumerate(items):
                # Sanitize the name for PubChem
                search_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', item).strip()

                with res_cols[idx % 2]:
                    try:
                        results = pcp.get_compounds(search_name, 'name')
                        if results:
                            c = results[0]
                            st.success(f"**{item}**")
                            st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{c.cid}/record/PNG")
                        else:
                            st.info(f"**{item}** (No match found)")
                    except Exception:
                        st.error(f"Search failed for {item}")