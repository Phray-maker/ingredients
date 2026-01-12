import streamlit as st
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import pubchempy as pcp
import re
import shutil
from streamlit_cropper import st_cropper

# --- TESSERACT CONFIG ---
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")

# Initialize Session State
if 'ocr_result' not in st.session_state:
    st.session_state.ocr_result = ""

st.title("🔬 Precision Ingredient Scanner")

uploaded_file = st.sidebar.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 1. Open and Resize if necessary (prevents Cloud memory lag)
    img = Image.open(uploaded_file).convert('RGB')
    if img.size[0] > 1800:
        img.thumbnail((1800, 1800))

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("1. Position Crop Area")

        # We use a unique key and disable 'realtime_update' for the return value
        # to stop the 'snapping' loop, but keep the UI responsive.
        cropped_img = st_cropper(
            img,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=None,
            key='cropper_v1'
        )

        # FIX FOR YOUR ERROR: Check if cropped_img exists before showing it
        if cropped_img:
            st.write("Preview of selection:")
            st.image(cropped_img, use_container_width=True)
        else:
            st.warning("Please define a crop area.")

    with col_right:
        st.subheader("2. OCR & Analysis")

        # Only run OCR when the button is pressed (prevents lag)
        if st.button("Extract Text 🔍", use_container_width=True):
            if cropped_img:
                with st.spinner("OCR in progress..."):
                    # Pre-processing: Grayscale and Contrast boost
                    proc = ImageOps.grayscale(cropped_img)
                    proc = ImageEnhance.Contrast(proc).enhance(2.5)

                    text = pytesseract.image_to_string(proc, config='--oem 3 --psm 6')

                    # Regex to find ingredients block
                    match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', text, re.DOTALL)
                    st.session_state.ocr_result = match.group(1) if match else text
            else:
                st.error("No selection found to OCR.")

        # Text area linked to session state
        final_text = st.text_area(
            "Verify Ingredients (Comma separated):",
            value=st.session_state.ocr_result,
            height=200
        )
        # Sync changes back to state
        st.session_state.ocr_result = final_text

        if st.button("Search PubChem 🚀", use_container_width=True):
            # Split and filter
            ingredients = [i.strip() for i in re.split(r'[,\n]', final_text) if len(i.strip()) > 2]

            for ing in ingredients:
                # Remove extra symbols/parentheses for better API matching
                clean_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', ing).strip()
                try:
                    res = pcp.get_compounds(clean_name, 'name')
                    if res:
                        st.success(f"**{ing}**")
                        st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{res[0].cid}/record/PNG",
                                 width=150)
                    else:
                        st.info(f"**{ing}** - (No PubChem match)")
                except:
                    st.error(f"Error searching: {ing}")