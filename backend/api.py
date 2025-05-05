from fastapi import FastAPI, UploadFile, Depends, HTTPException
from paddleocr import PaddleOCR
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from db import init_db, get_session
from models import Job
from sqlmodel import Session
from minio import Minio
from PIL import Image
import numpy as np
import cv2
import torch
import uuid
import io
import json

# Initialize MinIO
minio_client = Minio(
    "minio:9000",  # Service name from docker-compose
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False  # Because we're using HTTP, not HTTPS
)

bucket_name = "ocr-images"

# Ensure bucket exists
if not minio_client.bucket_exists(bucket_name):
    minio_client.make_bucket(bucket_name)

# Initialize FastAPI app
app = FastAPI(on_startup=[init_db])

# Initialize OCR and translation models
device = torch.device("cpu")
ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False)
tokenizer = AutoTokenizer.from_pretrained("phuckhangne/nllb-200-600M-finetuned-VN")
model = AutoModelForSeq2SeqLM.from_pretrained("phuckhangne/nllb-200-600M-finetuned-VN").to(device)

def translate_text(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True).to(device)
    out = model.generate(**inputs)
    return tokenizer.decode(out[0], skip_special_tokens=True)

@app.post("/process-image/", response_model=Job)
async def process_image(
    file: UploadFile,
    session: Session = Depends(get_session)
):
    #Read image and generate UUID
    image_bytes = await file.read()
    image_id = str(uuid.uuid4())
    #image_ext = file.filename.split('.')[-1]
    object_name = f"{image_id}.jpg"
    content_type = file.content_type or 'application/octet-stream' or 'image/jpeg'  # Default to JPEG if content type is not provided
    #Upload to MinIO
    minio_client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,  # This should still be the object name
        data=io.BytesIO(image_bytes),
        length=len(image_bytes),
        content_type=content_type,  # Use the corrected content type
        metadata={
            "Content-Disposition": f'inline; filename="{object_name}"'
        }
    )

    #Create job record in DB
    job = Job(
        image_path=object_name,
        status="processing"
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    #Process image (OCR + Translation)
    try:
        image = Image.open(io.BytesIO(image_bytes))
        img_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        ocr_results = ocr.ocr(img_bgr, cls=True)[0]
        translated_results = []

        for box, (txt, conf) in ocr_results:
            translated_text = translate_text(txt)
            translated_results.append({
                "box": box,
                "original_text": txt,
                "translated_text": translated_text
            })

        # Update DB job record
        job.ocr_data = json.dumps([r["original_text"] for r in translated_results])
        job.translation = json.dumps([r["translated_text"] for r in translated_results])
        polygons = [r["box"] for r in translated_results]
        job.box = polygons       
        job.status = "complete"
        session.add(job)
        session.commit()
        session.refresh(job)

    except Exception as e:
        job.status = "failed"
        session.add(job)
        session.commit()
        raise HTTPException(500, detail=str(e))

    return job
