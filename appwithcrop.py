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

# --- SESSION STATE MANAGEMENT ---
# Store the OCR text
if 'ocr_result' not in st.session_state:
    st.session_state.ocr_result = ""

# Store the crop box coordinates so they persist after button clicks
if 'last_coords' not in st.session_state:
    # Default starting box (left, top, width, height)
    st.session_state.last_coords = {'left': 10, 'top': 10, 'width': 80, 'height': 30}


@st.cache_data
def load_and_prep_image(file):
    image = Image.open(file).convert('RGB')
    if image.size[0] > 1800:
        image.thumbnail((1800, 1800))
    return image


st.title("🔬 Precision Ingredient Scanner")

uploaded_file = st.sidebar.file_uploader("Upload product label", type=["jpg", "png", "jpeg"], key="uploader")

if uploaded_file:
    img = load_and_prep_image(uploaded_file)

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.subheader("1. Position Crop Area")

        # We use the 'last_coords' from session state to keep the box where it was
        # This prevents the 'snap to top' behavior on rerun
        rect = st_cropper(
            img,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=None,
            return_type='box',
            should_resize_canvas=True,
            key='cropper_final'
        )

        # Immediately save the current position to state
        if rect:
            st.session_state.last_coords = rect

        # Perform the actual crop based on the box coordinates
        left, top, width, height = rect['left'], rect['top'], rect['width'], rect['height']
        # Strict boundary crop to prevent 'trailing text'
        final_crop = img.crop((left, top, left + width, top + height))

    with col_right:
        st.subheader("2. OCR & Analysis")

        if st.button("Extract Text 🔍", use_container_width=True):
            if final_crop:
                with st.spinner("Extracting strictly within bounds..."):
                    # Enhance image for Tesseract
                    proc = ImageOps.grayscale(final_crop)
                    proc = ImageEnhance.Contrast(proc).enhance(2.5)

                    # --psm 6: Assumes a single uniform block of text
                    # This tells Tesseract NOT to look for text outside this crop
                    text = pytesseract.image_to_string(proc, config='--oem 3 --psm 6')

                    # Cleanup result
                    match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', text, re.DOTALL)
                    st.session_state.ocr_result = match.group(1) if match else text
            else:
                st.error("No selection found.")

        # Text area synced to state
        final_text = st.text_area(
            "Verify Ingredients (Comma separated):",
            value=st.session_state.ocr_result,
            height=250
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