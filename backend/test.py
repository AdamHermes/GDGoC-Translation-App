from fastapi import FastAPI, UploadFile, Depends, HTTPException
from paddleocr import PaddleOCR
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from db import init_db, get_session
from models import Job, Text
from sqlmodel import Session
from minio import Minio
from PIL import Image
from utils import TextRequest
import numpy as np
import cv2
import torch
import uuid
import io
import json
import os
import traceback

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

# init MinIO
minio_client = Minio(MINIO_HOST, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
if not minio_client.bucket_exists(BUCKET):
    minio_client.make_bucket(BUCKET)

# FastAPI app
app = FastAPI(on_startup=[init_db])

device = torch.device("cpu")
ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False)

# Translation model (VN finetuned)
tokenizer = AutoTokenizer.from_pretrained("phuckhangne/nllb-200-600M-finetuned-VN")
model     = AutoModelForSeq2SeqLM.from_pretrained("phuckhangne/nllb-200-600M-finetuned-VN").to(device)
model.eval()



def translate_text(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True).to(device)
    out = model.generate(**inputs)
    return tokenizer.decode(out[0], skip_special_tokens=True)




@app.post("/process-image/", response_model=Job)
async def process_image(file: UploadFile, session: Session = Depends(get_session)):
    data = await file.read()
    img_id = str(uuid.uuid4())
    obj = f"{img_id}.jpg"
    ctype = file.content_type or 'image/jpeg'
    # upload raw
    try:
        minio_client.put_object(BUCKET, obj, io.BytesIO(data), len(data), content_type=ctype)
    except Exception:
        traceback.print_exc()
        raise HTTPException(500, "Storage upload failed")

    job = Job(image_path=obj, status="processing")
    session.add(job); session.commit(); session.refresh(job)


    try:
        image = Image.open(io.BytesIO(data))
        img_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        ocr_results = ocr.ocr(img_bgr, cls=True)[0]
        translated_results = []
        print("Translate Pending")
        for box, (txt, conf) in ocr_results:
            translated_text = translate_text(txt)
            translated_results.append({
                "box": box,
                "original_text": txt,
                "translated_text": translated_text
            })
        print("Translate Success")
        job.ocr_data    = json.dumps([r["original_text"]    for r in translated_results], ensure_ascii=False)
        job.translation = json.dumps([r["translated_text"] for r in translated_results], ensure_ascii=False)
        job.box         = [r["box"] for r in translated_results]
        job.status      = "complete"
        session.add(job); session.commit(); session.refresh(job)
    except Exception:
        traceback.print_exc()
        job.status = "failed"
        session.add(job); session.commit()
        raise HTTPException(500, "Processing failed")

    return job

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
        translated_text = translate_text(request.text)
        text = Text(ocr_data=request.text, translation=translated_text)
        session.add(text)
        session.commit()
        session.refresh(text)
        return {"translated_text": translated_text}
    except Exception as e:
        raise HTTPException(500, detail=str(e))