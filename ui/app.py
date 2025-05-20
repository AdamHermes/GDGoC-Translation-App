import streamlit as st

from PIL import Image, ImageDraw, ImageFont

import requests
import numpy as np
import json
import pandas as pd
import io
from pdf2image import convert_from_bytes
from docx import Document
import os

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

#-----------------------------------------------------------------------------
#                           CONFIG OF APP
#-----------------------------------------------------------------------------
st.title("Image Text Translator")

# Lang Dir
LANG_PATH = os.path.join("/model/langs.csv")
LANG_DATAFRAME = pd.read_csv(LANG_PATH, sep = ',')

# File uploader
uploaded_file = st.file_uploader("Upload an image, PDF, or DOCX", type=["png", "jpg", "jpeg", "pdf", "docx"])
session = requests.Session()
retry = Retry(
    total =5,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504], 
    allowed_methods=["POST"],
    raise_on_status=False
)
adapter = HTTPAdapter(max_retries = retry)
session.mount("http://", adapter)
session.mount("https://",adapter)

#-----------------------------------------------------------------------------
#                           THE SIDEBAR
#-----------------------------------------------------------------------------
# with st.sidebar:
#     st.header("Custom settings for your model")

#     # Premium button
#     if st.button("Upgrade to Pro"):
#         pass

#-----------------------------------------------------------------------------
#                           SELECT LANGUAGE
#-----------------------------------------------------------------------------
st.subheader("Select your language")
lang_list = LANG_DATAFRAME["Lang"].dropna().tolist()
lang_display = st.selectbox("Choose your language", ["-- Select --"] + lang_list)

ocr_lang_code = None
nllb_lang_code = None

if lang_display != "-- Select --":
    row = LANG_DATAFRAME[LANG_DATAFRAME["Lang"] == lang_display].iloc[0]
    ocr_lang_code = row["PaddleOCR"]
    nllb_lang_code = row["NLLB200"]

    st.write(f"Debug - Selected language: {lang_display}")
    st.write(f"Debug - OCR code: {ocr_lang_code}, NLLB code: {nllb_lang_code}")

    # Post response to Backend
    try:
        lang_response = session.post(
            "http://backend:8000/set-lang/",
            params={"ocr_lang_code": ocr_lang_code,
                "nllb_lang_code": nllb_lang_code}
        )
        if lang_response.status_code == 200:
            st.success(lang_response.json())
        else:
            st.error(f"Got an error. Status code: {lang_response.status_code}")
            st.error(f"Response: {lang_response.text}")
    except Exception as e:
        st.error(f"Error making request: {str(e)}")
# Helper: process and translate image

def process_and_translate_image(image, image_bytes):
    with st.spinner("Processing image..."):
        response = session.post(
            "http://backend:8000/process-image/",
            files={"file": image_bytes}
        )
        if response.status_code == 200:
            job = response.json()
            boxes = job.get("box", [])
            ocr_list = json.loads(job.get("ocr_data", "[]"))
            translation_list = json.loads(job.get("translation", "[]"))

            draw = ImageDraw.Draw(image)
            font_path = "DejaVuSans.ttf"

            # compute average box height for font scaling
            heights = []
            for poly in boxes:
                box = np.array(poly).astype(int)
                y0, y1 = box[:,1].min(), box[:,1].max()
                heights.append(y1 - y0)
            avg_h = max(int(np.mean(heights)) if heights else 10, 1)
            base_size = max(int(avg_h * 0.8), 12)

            # draw translation
            for poly, orig, trans in zip(boxes, ocr_list, translation_list):
                box = np.array(poly).astype(int)
                x0, y0 = box[:,0].min(), box[:,1].min()
                x1, y1 = box[:,0].max(), box[:,1].max()
                # white background
                draw.rectangle([x0, y0, x1, y1], fill="white")
                size = base_size
                font = ImageFont.truetype(font_path, size=size)
                # shrink to fit
                w = draw.textbbox((x0,y0), trans, font=font)[2] - x0
                while w > (x1 - x0) and size > 10:
                    size -= 1
                    font = ImageFont.truetype(font_path, size=size)
                    w = draw.textbbox((x0,y0), trans, font=font)[2] - x0
                draw.text((x0, y0), trans, fill="black", font=font)

            # display and upload
            st.image(image, caption="Translated Image", use_container_width=True)
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            buf.seek(0)
            up = session.post(
                "http://backend:8000/upload-translated-image/",
                files={"file": ("translated.jpg", buf, "image/jpeg")}
            )
            if up.status_code == 200:
                st.success(f"Translated image saved as: {up.json().get('object_name')}")
            else:
                st.error("Failed to save translated image.")
        else:
            st.error("Image processing failed.")


def translate_text(text):
    with st.spinner("Translating text..."):
        resp = session.post(
            "http://backend:8000/translate-text/", json={"text": text}
        )
        if resp.status_code == 200 and resp.json().get("translated_text"):
            st.success(resp.json()["translated_text"])
        else:
            st.error("Translation failed.")


# File upload

if uploaded_file:
    ftype = uploaded_file.type
    # IMAGE
    if ftype.startswith("image"):
        img = Image.open(uploaded_file)
        st.image(img, caption="Uploaded Image", use_container_width=True)
        if st.button("Translate Image", key="translate_img"):
            process_and_translate_image(img, uploaded_file.getvalue())

    # PDF
    elif ftype == "application/pdf":
        if st.button("Translate PDF", key="translate_pdf"):
            pages = convert_from_bytes(uploaded_file.read())
            for i, pg in enumerate(pages):
                st.image(pg, caption=f"Page {i+1}", use_container_width=True)
                buf = io.BytesIO()
                pg.save(buf, format='JPEG')
                process_and_translate_image(pg, buf.getvalue())

    # DOCX
    elif ftype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        # extract text immediately
        doc = Document(uploaded_file)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        st.text_area("Extracted Text from DOCX", value=text, height=200)
        if st.button("Translate DOCX Text", key="translate_docx"):
            translate_text(text)

# Separate text input translator
st.header("Text Translator")
input_text = st.text_area("Enter text to translate:")
if st.button("Translate Text", key="translate_txt"):
    translate_text(input_text)
