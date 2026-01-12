import streamlit as st
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import pubchempy as pcp
import re
import shutil
from streamlit_cropper import st_cropper

# --- TESSERACT CONFIG ---
# This ensures it works both locally (Windows) and in the Cloud (Linux)
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")

# Initialize Session State for the text area
if 'ocr_result' not in st.session_state:
    st.session_state.ocr_result = ""

st.title("🔬 Precision Ingredient Scanner")

# Use a static key for the uploader to prevent state loss during reruns
uploaded_file = st.sidebar.file_uploader("Upload product label", type=["jpg", "png", "jpeg"], key="label_loader")

if uploaded_file:
    # Open and convert to RGB
    img = Image.open(uploaded_file).convert('RGB')

    # Optional: Downsize slightly if the file is massive to prevent Cloud timeouts
    if img.size[0] > 2000:
        img.thumbnail((2000, 2000))

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("1. Position Crop Area")

        # Setting realtime_update to True for smooth UI
        # Using a static key 'cropper_v1' is crucial to stop the "snapping" bug
        cropped_img = st_cropper(
            img,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=None,
            key='cropper_v1'
        )

        # FIXED: Use 'use_column_width' for backwards compatibility
        if cropped_img is not None:
            st.write("Preview of selection:")
            st.image(cropped_img, use_column_width=True)
        else:
            st.warning("Please define a crop area using the box above.")

    with col_right:
        st.subheader("2. OCR & Analysis")

        # The OCR button
        if st.button("Extract Text 🔍", use_container_width=True):
            if cropped_img is not None:
                with st.spinner("OCR in progress..."):
                    # Improve OCR quality: Convert to Gray and boost contrast
                    proc = ImageOps.grayscale(cropped_img)
                    proc = ImageEnhance.Contrast(proc).enhance(2.0)

                    text = pytesseract.image_to_string(proc, config='--oem 3 --psm 6')

                    # Look for the word 'Ingredients' and grab everything after it
                    match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', text, re.DOTALL)
                    st.session_state.ocr_result = match.group(1) if match else text
            else:
                st.error("Please select an area on the image first.")

        # Text area linked to the session state so edits persist
        final_text = st.text_area(
            "Verify Ingredients (Comma separated):",
            value=st.session_state.ocr_result,
            height=200
        )
        st.session_state.ocr_result = final_text

        if st.button("Search PubChem 🚀", use_container_width=True):
            st.divider()
            # Split items and clean up whitespace/short strings
            ingredients = [i.strip() for i in re.split(r'[,\n]', final_text) if len(i.strip()) > 2]

            for ing in ingredients:
                # Basic cleaning: remove parentheses content for better API matching
                clean_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', ing).strip()
                try:
                    res = pcp.get_compounds(clean_name, 'name')
                    if res:
                        st.success(f"**{ing}**")
                        # Display PubChem structure
                        st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{res[0].cid}/record/PNG",
                                 width=150)
                    else:
                        st.info(f"**{ing}** - No match found.")
                except Exception:
                    st.error(f"Search failed for: {ing}")