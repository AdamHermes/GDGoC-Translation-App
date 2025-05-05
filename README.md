# OCR Translation App 

This project uses Docker to run a full OCR translation pipeline, including:
- A PostgreSQL database
- A MinIO object storage server (S3-compatible)
- A FastAPI backend
- A Streamlit frontend

---

##  Folder Structure

├── backend/
├── ui/
├── postgres_data/
├── minio_data/
├── uploads/
├── .env <-- you must create this file
├── docker-compose.yml


---

## ⚙️ .env File Setup

You **must create a `.env` file** in the root of the project before running Docker.

Here’s an example `.env`:

```env
DATABASE_URL=postgresql://appuser:secret@postgres:5432/ocrtranslate
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
BACKEND_URL=http://backend:8000
```
 How to Run the App
✅ 1. Open Docker Desktop
Make sure Docker Desktop is running on your machine.

🔨 2. First-Time Run (build the images)
bash
Copy
Edit
docker-compose up --build
🚀 3. Run from Second Time Onward
bash
Copy
Edit
docker-compose up
Once running:

Backend (FastAPI): http://localhost:8000/docs

Frontend (Streamlit): http://localhost:8501

MinIO console: http://localhost:9001

🖼️ Viewing Uploaded Images in MinIO
Go to http://localhost:9001

Login with:

Username: minioadmin

Password: minioadmin

Select your bucket (e.g., ocr-images)

Click on any object → press the 3-dot menu → Download

Rename the downloaded file with the correct extension (e.g. .jpg, .png) if needed.

By default, downloaded files may not include the extension. You can manually rename them.

🗃️ Viewing Stored Data in PostgreSQL
Option 1: Using psql in Docker
bash
Copy
Edit
docker exec -it <postgres_container_name> psql -U appuser -d ocrtranslate
To find the container name:

bash
Copy
Edit
docker ps
Once inside:

sql
Copy
Edit
\x                            -- Enable expanded view
\dt                           -- List all tables
SELECT * FROM your_table LIMIT 1;
SELECT id, LEFT(translation, 100) FROM your_table; -- Preview long fields
