import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import numpy as np
import json
import io
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
# Title of the application
st.title("Image Text Translator")

# File uploader
uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
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

if uploaded_file is not None:
    # Display the uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_container_width=True)

    # Translate button
    if st.button("Translate Image"):
        with st.spinner("Processing..."):
            # Send the image to the FastAPI backend
            response = session.post(
                "http://backend:8000/process-image/",
                files={"file": uploaded_file.getvalue()}
            )   

            if response.status_code == 200:
                job = response.json()
                boxes = job["box"]                  # List of polygons
                ocr_list = json.loads(job["ocr_data"])
                translation_list = json.loads(job["translation"])

                results = []
                for polygon, txt, trans in zip(boxes, ocr_list, translation_list):
                    results.append({
                        "box": polygon,             # one polygon per detection
                        "original_text": txt,
                        "translated_text": trans
                    })
                # Display the OCR results
                # Draw translations on the image
                draw = ImageDraw.Draw(image)
                font_path = "DejaVuSans.ttf"  # Ensure this font is available
# Precompute average height of all bounding boxes
                heights = []
                for result in results:
                    box = np.array(result["box"]).astype(int)
                    if box.ndim == 1:
                        x0, y0, x1, y1 = box  # handle flat [x0, y0, x1, y1]
                    else:
                        y0 = box[:, 1].min()
                        y1 = box[:, 1].max()
                    heights.append(y1 - y0)

                avg_height = max(int(np.mean(heights)), 1)
                base_font_size = max(int(avg_height * 0.8), 1)

                # Draw text with consistent font size across all boxes
                for result in results:
                    box = np.array(result["box"]).astype(int)
                    if box.ndim == 1:
                        x0, y0, x1, y1 = box
                    else:
                        x0, y0 = box[:, 0].min(), box[:, 1].min()
                        x1, y1 = box[:, 0].max(), box[:, 1].max()

                    # Erase original text
                    draw.rectangle([x0, y0, x1, y1], fill="white")

                    # Draw translated text
                    translated_text = result["translated_text"]
                    size = base_font_size
                    font = ImageFont.truetype(font_path, size=size)

                    # Shrink font slightly only if necessary
                    w = draw.textbbox((x0, y0), translated_text, font=font)[2] - x0
                    while w > (x1 - x0) and size > 12:  # prevent too small fonts
                        size -= 1
                        font = ImageFont.truetype(font_path, size=size)
                        w = draw.textbbox((x0, y0), translated_text, font=font)[2] - x0

                    draw.text((x0, y0), translated_text, fill="black", font=font)


                # Display the translated image
                st.image(image, caption="Translated Image", use_container_width=True)
                # Save the translated image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format="JPEG")
                img_byte_arr.seek(0)

                # Upload translated image to MinIO via backend
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
                st.error("Failed to process the image. Please try again.")

st.header("Text Translator")

input_text = st.text_area("Enter a text:")

if st.button("Translate Text"):
    if input_text.strip() != "":
        response = requests.post("http://backend:8000/translate-text/",
                                json = {
                                    "text": input_text
                                    }
                                )
        if response.status_code == 200:
            translated_text = response.json()["translated_text"]
            st.success(translated_text)
        else:
            st.error(f"Got error!")
    else:
        st.warning("You haven't entered a text yet.")