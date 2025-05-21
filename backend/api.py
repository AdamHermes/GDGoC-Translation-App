from fastapi import FastAPI, UploadFile, Depends, HTTPException, Query
from paddleocr import PaddleOCR
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from db import init_db, get_session
from models import Job, Text
from sqlmodel import Session
from minio import Minio
from PIL import Image
from utils import TextRequest
from itertools import islice
import numpy as np
import cv2
import torch
import uuid
import io
import json
import os
import traceback
import logging

# Hard limit threads
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# MinIO config
env = os.environ
MINIO_HOST = env.get("MINIO_HOST", "minio:9000")
MINIO_ACCESS_KEY = env.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = env.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = env.get("MINIO_SECURE", "False").lower() in ("true","1")
BUCKET = env.get("MINIO_BUCKET", "ocr-images")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# init MinIO
minio_client = Minio(MINIO_HOST, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
if not minio_client.bucket_exists(BUCKET):
    minio_client.make_bucket(BUCKET)

# FastAPI app
app = FastAPI(on_startup=[init_db])

device_str = "cpu"
if torch.backends.mps.is_available() and torch.backends.mps.is_built():
    device_str = "mps"
if torch.cuda.is_available():
    device_str = "cuda"
device = torch.device(device_str)

loaded_models = {}

logger.info("Loading PaddleOCR model...")
use_gpu = True if device == "cuda" else False
inference_model_path = "/inference_model"

if os.path.exists(inference_model_path):
    print("Loading model locally")
    ocr_en = PaddleOCR(
        det_model_dir=inference_model_path,
        use_angle_cls=True,
        lang="en",
        use_gpu=False,
        show_log=False
    )
else:
    ocr_en = PaddleOCR(
        use_angle_cls=True,
        lang="en",
        use_gpu=False,
        show_log=False
    )
ocr = None
ocr_ch = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=use_gpu, show_log = False)
logger.info(f"PaddleOCR loaded successfully on {device}")
langcode = "en"  # Default language code

loaded_models["en"] = ocr_en
loaded_models["ch"] = ocr_ch

# Translation model (VN finetuned)
nllb_lang = "eng_Latn"
logger.info("Loading translation model and tokenizer...")

tokenizer = AutoTokenizer.from_pretrained("phuckhangne/nllb-200-600M-finetuned-VN")
tokenizer.tgt_lang = "vie_Latn"

model     = AutoModelForSeq2SeqLM.from_pretrained("phuckhangne/nllb-200-600M-finetuned-VN").to(device)
model.eval()

logger.info(f"Translation model loaded successfully on {device}")

def get_ocr_model(lang_code: str):
    if lang_code not in loaded_models:
        supported_langs_on_demand = ["fr", "german", "japan", "korean", "es", "it", "ru", "ar"]
        if lang_code in supported_langs_on_demand:
            logger.info(f"Cache miss. Loading PaddleOCR model for language: {lang_code}...")
            try:
                loaded_models[lang_code] = PaddleOCR(use_angle_cls=True, lang=lang_code, use_gpu=use_gpu, show_log=False)
                logger.info(f"PaddleOCR model for {lang_code} loaded and cached.")
            except Exception as e:
                logger.error(f"Failed to load OCR model for {lang_code}: {e}. Defaulting to English model.")
                return loaded_models["en"] 
        else:
            logger.warning(f"OCR language '{lang_code}' not pre-loaded or in on-demand list. Defaulting to English model.")
            return loaded_models["en"] 
    return loaded_models[lang_code]

def _batch_translate_core(texts: list[str], nllb_src_lang: str) -> list[str]:
    if not texts:
        return []

    valid_texts = [t for t in texts if isinstance(t, str) and t.strip()]
    if not valid_texts:
        return []

    tokenizer.src_lang = nllb_src_lang
    inputs = tokenizer(valid_texts, return_tensors="pt", padding=True, truncation=True).to(device)

    outputs = model.generate(**inputs)

    return [tokenizer.decode(t, skip_special_tokens=True) for t in outputs]

def translate_text(text, nllb_lang: str = "eng_Latn") -> str:
    translated_texts = _batch_translate_core([text], nllb_lang)
    return translated_texts[0] if translated_texts else ""

def translate_image(text: list[str], nllb_lang: str = "eng_Latn") -> list[str]:
    return _batch_translate_core(text, nllb_lang)

@app.post("/set-lang/")
async def set_lang(ocr_lang_code: str, nllb_lang_code: str, session: Session = Depends(get_session)):
    global langcode, nllb_lang
    try:
        langcode = ocr_lang_code # Validate language codes
        nllb_lang = nllb_lang_code
        return {"message": "Language codes set successfully"}
    except Exception as e:
        logging.error(f"Error setting language: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to set language codes")

@app.post("/process-image/", response_model=Job)
async def process_image(
    file: UploadFile,
    session: Session = Depends(get_session)
):
    try:
        data = await file.read()
        img_id = str(uuid.uuid4())
        obj = f"{img_id}.jpg"
        ctype = file.content_type or 'image/jpeg'
        print("The loaded langcode is: ", langcode)
        ocr = get_ocr_model(langcode)    
        # upload raw
        try:
            minio_client.put_object(BUCKET, obj, io.BytesIO(data), len(data), content_type=ctype)
        except Exception:
            traceback.print_exc()
            raise HTTPException(500, "Storage upload failed")

        # Create job record in DB
        job = Job(image_path=obj, status="processing")
        session.add(job)
        session.commit()
        session.refresh(job)

        # Process image (OCR + Translation)
        try:
            image = Image.open(io.BytesIO(data))
            img_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            ocr_results = ocr.ocr(img_bgr, cls=True)
            if not ocr_results or not ocr_results[0]:
                raise HTTPException(400, detail="OCR did not detect any text")
            ocr_results = ocr_results[0]

            translated_results = []
            boxes, originals = zip(*[(box, txt) for box, (txt, _) in ocr_results])
            translations = translate_image(list(originals), nllb_lang)

            for box, orig, trans in zip(boxes, originals, translations):
                translated_results.append({
                    "box": box,
                    "original_text": orig,
                    "translated_text": trans
                })

            # Update DB job record
            job.ocr_data = json.dumps([r["original_text"] for r in translated_results])
            job.translation = json.dumps([r["translated_text"] for r in translated_results])
            job.box = [r["box"] for r in translated_results]
            job.status = "complete"
            session.add(job)
            session.commit()
            session.refresh(job)

        except Exception as e:
            logging.error(f"Error processing image: {str(e)}")
            job.status = "failed"
            session.add(job)
            session.commit()
            raise HTTPException(500, detail=f"Processing failed: {str(e)}")

        return job

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(500, detail=f"Unexpected error: {str(e)}")

@app.post("/upload-translated-image/")
async def upload_translated_image(file: UploadFile):
    data = await file.read()
    img_id = str(uuid.uuid4())
    obj = f"translated-{img_id}.jpg"
    try:
        minio_client.put_object(BUCKET, obj, io.BytesIO(data), len(data), content_type=file.content_type or 'image/jpeg')
    except Exception:
        traceback.print_exc()
        raise HTTPException(500, "Storage upload failed")
    return {"object_name": obj}

@app.post('/translate-text/')
async def translate_text_api(request: TextRequest, session: Session = Depends(get_session)):
    try:
        translated_text = translate_text(request.text, nllb_lang)
        text = Text(ocr_data=request.text, translation=translated_text)
        session.add(text)
        session.commit()
        session.refresh(text)
        return {"translated_text": translated_text}
    except Exception as e:
        raise HTTPException(500, detail=str(e))