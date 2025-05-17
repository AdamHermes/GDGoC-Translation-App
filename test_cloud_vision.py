from paddleocr import PaddleOCR
from PIL import Image
import numpy as np

# Load models
detector = PaddleOCR(det=True, rec=False, use_angle_cls=True)
rec_latin = PaddleOCR(det=False, rec=True, use_angle_cls=True, lang='latin')
rec_ch = PaddleOCR(det=False, rec=True, use_angle_cls=True, lang='ch')

# Load image
img = Image.open("ch3.png").convert("RGB")
img_np = np.array(img)

# Detect boxes
dt_results = detector.ocr(img_np, cls=True)[0]

final_results = []
for box, _ in dt_results:
    x1, y1 = map(int, box[0])
    x2, y2 = map(int, box[2])
    crop = img.crop((x1, y1, x2, y2))

    # Recognize with both models
    r1 = rec_latin.ocr(np.array(crop), det=False, cls=False)[0]
    r2 = rec_ch.ocr(np.array(crop), det=False, cls=False)[0]

    txt1, conf1 = r1[0]
    txt2, conf2 = r2[0]

    # Choose higher-confidence
    if conf1 >= conf2:
        det_lng = "en"
        final_results.append((box, txt1, conf1, det_lng))
    else:
        det_lng = "ch"
        final_results.append((box, txt2, conf2, det_lng))

# Print results
for box, text, conf, det_lng in final_results:
    print(f"{text} ({conf:.2f}), detected in {det_lng} language")
