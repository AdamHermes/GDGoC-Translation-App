import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import numpy as np
import json
# Title of the application
st.title("Image Text Translator")

# File uploader
uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Display the uploaded image
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_container_width=True)

    # Translate button
    if st.button("Translate"):
        with st.spinner("Processing..."):
            # Send the image to the FastAPI backend
            response = requests.post(
                "http://backend:8000/process-image/",
                files={"file": uploaded_file.getvalue()},
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
                for result in results:
                    box = np.array(result["box"]).astype(int)
                    x0, y0 = box[:, 0].min(), box[:, 1].min()
                    x1, y1 = box[:, 0].max(), box[:, 1].max()

                    # Erase original text
                    draw.rectangle([x0, y0, x1, y1], fill="white")

                    # Draw translated text
                    translated_text = result["translated_text"]
                    h = y1 - y0
                    size = max(int(h * 0.8), 1)
                    font = ImageFont.truetype(font_path, size=size)

                    # If text is too wide, shrink until it fits
                    w = draw.textbbox((x0, y0), translated_text, font=font)[2] - x0
                    while w > (x1 - x0) and size > 1:
                        size -= 1
                        font = ImageFont.truetype(font_path, size=size)
                        w = draw.textbbox((x0, y0), translated_text, font=font)[2] - x0
                    draw.text((x0, y0), translated_text, fill="black", font=font)

                # Display the translated image
                st.image(image, caption="Translated Image", use_container_width=True)
            else:
                st.error("Failed to process the image. Please try again.")