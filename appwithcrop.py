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

# --- 1. STATE INITIALIZATION ---
if 'ocr_result' not in st.session_state:
    st.session_state.ocr_result = ""


# --- 2. CACHING ---
@st.cache_data
def get_image(file):
    image = Image.open(file).convert('RGB')
    # Resize slightly to keep the web interface snappy
    if image.size[0] > 1500:
        image.thumbnail((1500, 1500))
    return image


st.title("🔬 Precision Ingredient Scanner")

uploaded_file = st.sidebar.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    img = get_image(uploaded_file)
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("1. Select Area")
        # We only ask for the 'box' coordinates.
        # This is the most stable return type for Streamlit Cloud.
        box = st_cropper(
            img,
            realtime_update=True,
            box_color='red',
            aspect_ratio=None,
            return_type='box',
            key='stable_crop_box'
        )

        # Manually crop using PIL to ensure no trailing text
        left, top, width, height = box['left'], box['top'], box['width'], box['height']
        cropped_img = img.crop((left, top, left + width, top + height))

    with col_right:
        st.subheader("2. OCR & Results")

        if st.button("Extract Text 🔍", use_container_width=True):
            with st.spinner("Processing..."):
                # Pre-process for OCR clarity
                proc = ImageOps.grayscale(cropped_img)
                proc = ImageEnhance.Contrast(proc).enhance(2.0)

                # Run OCR - PSM 6 is best for blocks of text like ingredient lists
                raw_text = pytesseract.image_to_string(proc, config='--oem 3 --psm 6')

                # Basic cleanup
                clean = re.sub(r'\s+', ' ', raw_text).strip()
                st.session_state.ocr_result = clean

        # Editable Result
        edited_text = st.text_area("Edit Ingredients:", value=st.session_state.ocr_result, height=200)
        st.session_state.ocr_result = edited_text

        if st.button("Search PubChem 🚀", use_container_width=True):
            ingredients = [i.strip() for i in re.split(r'[,\n]', edited_text) if len(i.strip()) > 2]
            for item in ingredients:
                try:
                    # Strip extra characters for search
                    search_term = re.sub(r'[^a-zA-Z0-9 ]', '', item)
                    res = pcp.get_compounds(search_term, 'name')
                    if res:
                        st.success(f"**{item}**")
                        st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{res[0].cid}/record/PNG",
                                 width=150)
                except:
                    continue