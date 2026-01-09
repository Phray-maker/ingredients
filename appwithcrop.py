import streamlit as st
import pytesseract
from PIL import Image, ImageDraw
import pubchempy as pcp
import re
import shutil

# --- TESSERACT CONFIG ---
if not shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Chemical Scanner", layout="wide")

if 'verified_text' not in st.session_state:
    st.session_state['verified_text'] = ""

st.title("🔬 Precision Ingredient Scanner")

uploaded_file = st.file_uploader("Upload product label", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 1. Load Original Image
    img = Image.open(uploaded_file).convert('RGB')
    w, h = img.size

    col_crop, col_zoom, col_text = st.columns([1, 1, 1.2])

    with col_crop:
        st.subheader("1. Position Crop")
        # Native Sliders for cloud stability
        left_p = st.slider("Left %", 0, 100, 10)
        right_p = st.slider("Right %", 0, 100, 90)
        top_p = st.slider("Top %", 0, 100, 30)
        bottom_p = st.slider("Bottom %", 0, 100, 70)

        # Pixel coords
        left, right = int(w * left_p / 100), int(w * right_p / 100)
        top, bottom = int(h * top_p / 100), int(h * bottom_p / 100)

        # Main Preview
        preview_img = img.copy()
        draw = ImageDraw.Draw(preview_img)
        draw.rectangle([left, top, right, bottom], outline="red", width=20)
        st.image(preview_img, caption="Global View", use_column_width=True)

    with col_zoom:
        st.subheader("2. Zoom View")
        # Ensure the crop is valid (not zero width/height)
        if right > left and bottom > top:
            zoom_crop = img.crop((left, top, right, bottom))
            # Display magnified crop
            st.image(zoom_crop, caption="Precision Loupe (Target)", use_column_width=True)

            if st.button("Run OCR on Zoom View 🔍", use_container_width=True):
                with st.spinner("Reading ingredients..."):
                    # PSM 6 for structured lists
                    raw_text = pytesseract.image_to_string(zoom_crop, config='--oem 3 --psm 6')
                    clean_match = re.search(r'(?i)ingredients?[:\-\s]+(.*)', raw_text, re.DOTALL)
                    st.session_state['verified_text'] = clean_match.group(1) if clean_match else raw_text
        else:
            st.warning("Invalid selection area.")

    with col_text:
        st.subheader("3. Verify & Search")
        user_text = st.text_area("Edit findings:", value=st.session_state['verified_text'], height=250)
        st.session_state['verified_text'] = user_text

        if st.button("Search PubChem 🚀", use_container_width=True):
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
                    st.error(f"Error: {item}")