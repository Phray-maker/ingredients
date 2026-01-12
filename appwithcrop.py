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


# --- CACHING STRATEGY ---
# This is the most important part to stop the snapping.
# It ensures the 'img' object doesn't change IDs between reruns.
@st.cache_data
def load_and_prep_image(file):
    image = Image.open(file).convert('RGB')
    if image.size[0] > 1800:
        image.thumbnail((1800, 1800))
    return image


if 'ocr_result' not in st.session_state:
    st.session_state.ocr_result = ""

st.title("🔬 Precision Ingredient Scanner")

uploaded_file = st.sidebar.file_uploader("Upload product label", type=["jpg", "png", "jpeg"], key="uploader")

if uploaded_file:
    # Use the cached function
    img = load_and_prep_image(uploaded_file)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("1. Position Crop Area")

        # Setting realtime_update=False often solves the snapping in Cloud environments
        # because it only updates the state ONCE when you let go of the mouse.
        cropped_img = st_cropper(
            img,
            realtime_update=False,
            box_color='#FF0000',
            aspect_ratio=None,
            key='main_cropper_v2'
        )

        if cropped_img is not None:
            st.write("Current selection:")
            st.image(cropped_img, use_column_width=True)

    with col_right:
        st.subheader("2. OCR & Analysis")

        if st.button("Extract Text 🔍", use_container_width=True):
            if cropped_img is not None:
                with st.spinner("Processing..."):
                    proc = ImageOps.grayscale(cropped_img)
                    proc = ImageEnhance.Contrast(proc).enhance(2.0)
                    text = pytesseract.image_to_string(proc, config='--oem 3 --psm 6')
                    match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', text, re.DOTALL)
                    st.session_state.ocr_result = match.group(1) if match else text

        final_text = st.text_area(
            "Verify Ingredients:",
            value=st.session_state.ocr_result,
            height=200
        )
        st.session_state.ocr_result = final_text

        if st.button("Search PubChem 🚀", use_container_width=True):
            st.divider()
            items = [i.strip() for i in re.split(r'[,\n]', final_text) if len(i.strip()) > 2]
            for item in items:
                clean_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', item).strip()
                try:
                    res = pcp.get_compounds(clean_name, 'name')
                    if res:
                        st.success(f"**{item}**")
                        st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{res[0].cid}/record/PNG",
                                 width=150)
                    else:
                        st.info(f"**{item}** - No match.")
                except:
                    st.error(f"Error: {item}")