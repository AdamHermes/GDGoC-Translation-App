# OCR Translation App

This project uses Docker to run a full OCR translation pipeline, including:

- A PostgreSQL database
- A MinIO object storage server (S3-compatible)
- A FastAPI backend
- A Streamlit frontend

---

## Folder Structure

```
├── backend/
├── ui/
├── postgres_data/
├── minio_data/
├── uploads/
├── .env <-- you must create this file
├── docker-compose.yml
```

---

## ⚙️ .env File Setup

You **must create a `.env` file** in the root of the project before running Docker.

Here’s an example `.env`:

```
DATABASE_URL=postgresql://appuser:secret@postgres:5432/ocrtranslate
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
BACKEND_URL=http://backend:8000
```

---

## How to Run the App

1. **Open Docker Desktop**  
   Make sure Docker Desktop is running on your machine.

2. **First-Time Run (build the images)**  
   ```
   docker-compose up --build
   ```

3. **Run from Second Time Onward**  
   ```
   docker-compose up
   ```

Once running:

- **Backend (FastAPI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend (Streamlit):** [http://localhost:8501](http://localhost:8501) (Go into this link to test the web app)
- **MinIO console:** [http://localhost:9001](http://localhost:9001)

---

##  Viewing Uploaded Images in MinIO

1. Go to [http://localhost:9001](http://localhost:9001)
2. Login with:
   - **Username:** minioadmin (default)
   - **Password:** minioadmin (default)
3. Select your bucket (e.g., ocr-images)
4. Click on any object → press the 3-dot menu → Download
5. Rename the downloaded file with the correct extension (e.g., .jpg, .png) if needed.


---

## 🗃️ Viewing Stored Data in PostgreSQL

In terminal in the project root folder:

1. Find the PostgreSQL container name:  
   ```
   docker ps
   ```

2. Connect to the database:  
   ```
   docker exec -it <postgres_container_name> psql -U appuser -d ocrtranslate
   ```

3. Once inside, you can run SQL commands:  
   ```
   \x                            -- Enable expanded view
   \dt                           -- List all tables
   SELECT * FROM your_table LIMIT 5; (default your_table = job)
   SELECT ocr_data FROM your_table WHERE id = id_number; x-- Preview long fields, id_number can be viewed from the above line
   ```

---
