import streamlit as st
import pytesseract
from PIL import Image, ImageDraw
import pubchempy as pcp
import re
import shutil
import numpy as np

# --- TESSERACT CONFIG ---
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")

if 'verified_text' not in st.session_state:
    st.session_state['verified_text'] = ""

st.title("🔬 Interactive Chemical Scanner")

uploaded_file = st.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 1. Load and Standardize Image
    img = Image.open(uploaded_file).convert('RGB')
    w, h = img.size

    col_crop, col_text = st.columns([1, 1])

    with col_crop:
        st.subheader("Step 1: Define Crop Area")
        # Native Sliders: Immune to iframe/canvas bugs
        left_p = st.slider("Left Margin %", 0, 100, 10)
        right_p = st.slider("Right Margin %", 0, 100, 90)
        top_p = st.slider("Top Margin %", 0, 100, 30)
        bottom_p = st.slider("Bottom Margin %", 0, 100, 70)

        # Calculate pixel coordinates
        left, right = int(w * left_p / 100), int(w * right_p / 100)
        top, bottom = int(h * top_p / 100), int(h * bottom_p / 100)

        # Draw a preview box on a display copy
        preview_img = img.copy()
        draw = ImageDraw.Draw(preview_img)
        draw.rectangle([left, top, right, bottom], outline="red", width=15)

        # Display the preview using standard st.image (which you confirmed works)
        st.image(preview_img, caption="Red box shows area for OCR", use_container_width=True)

    with col_text:
        st.subheader("Step 2: Read & Verify")

        if st.button("Run OCR on Red Box 🔍"):
            # Crop the high-res original based on sliders
            ocr_crop = img.crop((left, top, right, bottom))

            with st.spinner("Extracting text..."):
                # PSM 6: Uniform block of text
                raw_text = pytesseract.image_to_string(ocr_crop, config='--oem 3 --psm 6')

                # Cleanup: look for 'Ingredients' header
                clean_match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', raw_text, re.DOTALL)
                st.session_state['verified_text'] = clean_match.group(1) if clean_match else raw_text

        # Interactive text area for manual fixes
        user_text = st.text_area("Tweak detected ingredients:", value=st.session_state['verified_text'], height=250)
        st.session_state['verified_text'] = user_text

        if st.button("Check PubChem 🚀"):
            st.divider()
            items = [i.strip() for i in re.split(r'[,\n]', user_text) if len(i.strip()) > 2]

            for item in items:
                search_name = re.sub(r'\(.*?\)|[^a-zA-Z0-9 ]', '', item).strip()
                try:
                    results = pcp.get_compounds(search_name, 'name')
                    if results:
                        st.success(f"**{item}**")
                        st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{results[0].cid}/record/PNG")
                    else:
                        st.info(f"**{item}** (No match)")
                except:
                    st.error(f"Search failed for {item}")