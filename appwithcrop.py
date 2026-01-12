import streamlit as st
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import pubchempy as pcp
import re
from streamlit_cropper import st_cropper

# --- CONFIG ---
# Standard Cloud Tesseract pathing
import shutil

if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")

# --- UI STATE ---
if 'verified_text' not in st.session_state:
    st.session_state['verified_text'] = ""

st.title("🔬 Precision Ingredient Scanner")

uploaded_file = st.sidebar.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file).convert('RGB')

    col_crop, col_res = st.columns([1.5, 1])

    with col_crop:
        st.subheader("1. Select Ingredient Area")
        st.info("Drag the box over the ingredients list. Resize by pulling the corners.")

        # This component replaces ALL the slider logic
        # It returns a PIL Image of the cropped area in real-time
        cropped_img = st_cropper(img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)

        if st.button("Run OCR 🔍", use_container_width=True):
            with st.spinner("Extracting text..."):
                # Pre-processing for better OCR accuracy
                gray = ImageOps.grayscale(cropped_img)
                enhanced = ImageEnhance.Contrast(gray).enhance(2.0)

                raw_text = pytesseract.image_to_string(enhanced, config='--oem 3 --psm 6')

                # Regex cleanup
                clean_match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', raw_text, re.DOTALL)
                st.session_state['verified_text'] = clean_match.group(1) if clean_match else raw_text

    with col_res:
        st.subheader("2. Results & Search")
        user_text = st.text_area("Edit extracted text:", value=st.session_state['verified_text'], height=200)
        st.session_state['verified_text'] = user_text

        if st.button("Search PubChem 🚀", use_container_width=True):
            # Split by comma or newline
            items = [i.strip() for i in re.split(r'[,\n]', user_text) if len(i.strip()) > 2]

            for item in items:
                # Clean up names for better API matching
                search_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', item).strip()
                try:
                    results = pcp.get_compounds(search_name, 'name')
                    if results:
                        st.success(f"**{item}**")
                        st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{results[0].cid}/record/PNG",
                                 width=200)
                    else:
                        st.warning(f"**{item}**: No PubChem match.")
                except Exception:
                    st.error(f"Search failed for: {item}")