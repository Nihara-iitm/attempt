from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/upload/")
async def upload_data(
    doubts: str = Form(...),          # Text field
    file: UploadFile = File(...)           # File field
):
    contents = await file.read()
 

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "doubts": doubts,
        "file_size": len(contents)
    }