import streamlit as st
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import pubchempy as pcp
import re
from streamlit_cropper import st_cropper
import shutil

# --- COMPATIBILITY CHECK ---
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")

# Initialize state to keep results "sticky"
if 'ocr_result' not in st.session_state:
    st.session_state.ocr_result = ""

st.title("🔬 Precision Ingredient Scanner")

uploaded_file = st.sidebar.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file).convert('RGB')

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("1. Position Crop Area")
        # realtime_update=True is okay for visual feedback,
        # but realtime_update=False is more stable for OCR triggers.
        cropped_img = st_cropper(
            img,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=None,
            key='cropper'
        )

        # Display a small preview of what will be OCR'd
        st.write("Preview of selection:")
        st.image(cropped_img, use_container_width=True)

    with col_right:
        st.subheader("2. OCR & Analysis")

        if st.button("Extract Text from Selection 🔍", use_container_width=True):
            with st.spinner("OCR in progress..."):
                # Pre-processing for better accuracy
                proc = ImageOps.grayscale(cropped_img)
                proc = ImageEnhance.Contrast(proc).enhance(2.0)

                text = pytesseract.image_to_string(proc, config='--oem 3 --psm 6')

                # Try to isolate ingredients list
                match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', text, re.DOTALL)
                st.session_state.ocr_result = match.group(1) if match else text

        # Edit Area
        final_text = st.text_area(
            "Verify Ingredients (Comma separated):",
            value=st.session_state.ocr_result,
            height=200
        )
        st.session_state.ocr_result = final_text

        if st.button("Search PubChem 🚀", use_container_width=True):
            st.divider()
            # Split and clean names
            ingredients = [i.strip() for i in re.split(r'[,\n]', final_text) if len(i.strip()) > 2]

            for ing in ingredients:
                clean_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', ing).strip()
                try:
                    res = pcp.get_compounds(clean_name, 'name')
                    if res:
                        st.success(f"**{ing}** (CID: {res[0].cid})")
                        st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{res[0].cid}/record/PNG",
                                 width=150)
                    else:
                        st.info(f"**{ing}** - No match found.")
                except:
                    st.error(f"Error searching for: {ing}")