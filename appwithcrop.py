import streamlit as st
from streamlit_drawable_canvas import st_canvas
import pytesseract
from PIL import Image
import pubchempy as pcp
import re
import shutil
import numpy as np

# --- TESSERACT CONFIG ---
# Ensure the local path is correct for your Windows machine
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")

# Persistent storage for the detected text
if 'verified_text' not in st.session_state:
    st.session_state['verified_text'] = ""

st.title("🔬 Interactive Chemical Scanner")

uploaded_file = st.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file).convert('RGB')
    w, h = img.size

    # Standardize display size for the canvas
    display_width = 700
    scale = display_width / w
    display_height = int(h * scale)

    col_canvas, col_text = st.columns([1.2, 1])

    with col_canvas:
        st.subheader("Step 1: Select Ingredients Area")
        # Draw a box over the specific text block
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#ff8c00",
            background_image=img,
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

            # Check if a user has drawn a box
            if canvas_result.json_data and len(canvas_result.json_data["objects"]) > 0:
                obj = canvas_result.json_data["objects"][-1]

                # Convert canvas coordinates back to original image scale
                left = int(obj.get("left", 0) / scale)
                top = int(obj.get("top", 0) / scale)
                width = int((obj.get("width", 0) * obj.get("scaleX", 1)) / scale)
                height = int((obj.get("height", 0) * obj.get("scaleY", 1)) / scale)

                # Crop original high-res image for the sharpest OCR
                ocr_input_img = img.crop((left, top, left + width, top + height))

            with st.spinner("Processing text..."):
                # PSM 6 is optimized for uniform blocks/columns of text
                raw_text = pytesseract.image_to_string(ocr_input_img, config='--oem 3 --psm 6')

                # Cleanup: look for 'Ingredients' header inside the selection
                clean_match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', raw_text, re.DOTALL)
                st.session_state['verified_text'] = clean_match.group(1) if clean_match else raw_text

        # The interactive 'tweak' area to fix 'sorbale' -> 'sorbate'
        user_text = st.text_area("Tweak detected text:", value=st.session_state['verified_text'], height=250)
        st.session_state['verified_text'] = user_text

        if st.button("Check PubChem 🚀"):
            st.divider()
            # Split by comma or newline for the list
            items = [i.strip() for i in re.split(r'[,\n]', user_text) if len(i.strip()) > 2]

            res_cols = st.columns(2)
            for idx, item in enumerate(items):
                # Strip noise for search
                search_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', item).strip()

                with res_cols[idx % 2]:
                    try:
                        results = pcp.get_compounds(search_name, 'name')
                        if results:
                            c = results[0]
                            st.success(f"**{item}**")
                            # Pull PNG structure from PubChem
                            st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{c.cid}/record/PNG")
                        else:
                            st.info(f"**{item}** (No molecule found)")
                    except:
                        st.error(f"Error searching {item}")