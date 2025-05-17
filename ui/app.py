import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import numpy as np
import json
import io
from pdf2image import convert_from_bytes
from docx import Document
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
# Title of the application
st.title("Image Text Translator")

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

def process_and_translate_image(image, image_bytes):
    with st.spinner("Processing image..."):
        response = session.post(
            "http://backend:8000/process-image/",
            files={"file": image_bytes}
        )
        if response.status_code == 200:
            job = response.json()
            boxes = job["box"]
            ocr_list = json.loads(job["ocr_data"])
            translation_list = json.loads(job["translation"])

            draw = ImageDraw.Draw(image)
            font_path = "DejaVuSans.ttf"
            heights = []
            for polygon in boxes:
                box = np.array(polygon).astype(int)
                y0 = box[:, 1].min() if box.ndim > 1 else box[1]
                y1 = box[:, 1].max() if box.ndim > 1 else box[3]
                heights.append(y1 - y0)
            avg_height = max(int(np.mean(heights)), 1)
            base_font_size = max(int(avg_height * 0.8), 1)

            for polygon, txt, trans in zip(boxes, ocr_list, translation_list):
                box = np.array(polygon).astype(int)
                x0 = box[:, 0].min() if box.ndim > 1 else box[0]
                y0 = box[:, 1].min() if box.ndim > 1 else box[1]
                x1 = box[:, 0].max() if box.ndim > 1 else box[2]
                y1 = box[:, 1].max() if box.ndim > 1 else box[3]

                draw.rectangle([x0, y0, x1, y1], fill="white")
                font = ImageFont.truetype(font_path, size=base_font_size)
                w = draw.textbbox((x0, y0), trans, font=font)[2] - x0
                while w > (x1 - x0) and base_font_size > 12:
                    base_font_size -= 1
                    font = ImageFont.truetype(font_path, size=base_font_size)
                    w = draw.textbbox((x0, y0), trans, font=font)[2] - x0
                draw.text((x0, y0), trans, fill="black", font=font)

            st.image(image, caption="Translated Image", use_container_width=True)
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="JPEG")
            img_byte_arr.seek(0)

            upload_response = session.post(
                "http://backend:8000/upload-translated-image/",
                files={"file": ("translated.jpg", img_byte_arr, "image/jpeg")},
            )
            if upload_response.status_code == 200:
                object_name = upload_response.json()["object_name"]
                st.success(f"Translated image saved to MinIO as: {object_name}")
            else:
                st.error("Failed to save translated image to MinIO.")
        else:
            st.error("Failed to process the image.")
def translate_text(text):
    with st.spinner("Translating text..."):
        response = session.post("http://backend:8000/translate-text/", json={"text": text})
        if response.status_code == 200:
            st.success(response.json()["translated_text"])
        else:
            st.error("Text translation failed.")

if uploaded_file is not None:
    file_type = uploaded_file.type
    if st.button("Translate File"):
        if file_type.startswith("image"):
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_container_width=True)
            process_and_translate_image(image, uploaded_file.getvalue())
        
        elif file_type == "application/pdf":
            pages = convert_from_bytes(uploaded_file.read())
            for i, page_image in enumerate(pages):
                st.image(page_image, caption=f"Page {i+1}", use_container_width=True)
                img_bytes = io.BytesIO()
                page_image.save(img_bytes, format='JPEG')
                process_and_translate_image(page_image, img_bytes.getvalue())

        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            if "docx_text" not in st.session_state:
                doc = Document(uploaded_file)
                st.session_state.docx_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            
            st.text_area("Extracted Text from DOCX", value=st.session_state.docx_text, height=200)

            if st.button("Translate DOCX Text"):
                translate_text(st.session_state.docx_text)


st.header("Text Translator")

input_text = st.text_area("Enter a text:")

if st.button("Translate Text"):
    translate_text(input_text)