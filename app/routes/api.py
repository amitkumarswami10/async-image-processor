from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import uuid
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import ProcessingRequest, ImageData
from worker.tasks import process_image
import io
import csv

router = APIRouter()

# 📤 Upload CSV File
@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    try:
        contents = await file.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))

        # ✅ Validate Columns
        expected_columns = ['S. No.', 'Product Name', 'Input Image Urls']
        if list(df.columns) != expected_columns:
            raise HTTPException(status_code=400, detail=f"CSV must have columns: {expected_columns}")

        # 🔐 Generate Request ID
        request_id = str(uuid.uuid4())
        db: Session = SessionLocal()
        request_entry = ProcessingRequest(request_id=request_id, status="pending")
        db.add(request_entry)
        db.commit()
        db.refresh(request_entry)

        # 🖼️ Process Each Image Row
        for _, row in df.iterrows():
            product_name = row['Product Name']
            serial_number = row['S. No.']
            image_urls = [url.strip() for url in row['Input Image Urls'].split(',') if url.strip()]
            
            for input_url in image_urls:
                image = ImageData(
                    request_id=request_id,
                    serial_number=serial_number,
                    product_name=product_name,
                    input_url=input_url,
                    status="processing"
                )
                db.add(image)
                db.flush()  # Grab ID before commit
                process_image.delay(image.id, input_url)

        db.commit()
        db.close()

        return JSONResponse(content={"request_id": request_id})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# 📊 Check Status by Request ID
@router.get("/status")
def get_status(request_id: str = Query(...)):
    db = SessionLocal()

    try:
        request = db.query(ProcessingRequest).filter(ProcessingRequest.request_id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Invalid request_id")

        images = db.query(ImageData).filter(ImageData.request_id == request_id).all()

        # 🔁 Aggregate status
        statuses = [img.status for img in images]
        if all(s == "done" for s in statuses):
            request.status = "done"
        elif any(s == "failed" for s in statuses):
            request.status = "failed"
        else:
            request.status = "in_progress"
        db.commit()

        return {
            "request_id": request_id,
            "status": request.status,
            "images": [
                {
                    "input_url": img.input_url,
                    "output_url": img.output_url,
                    "status": img.status
                }
                for img in images
            ]
        }

    finally:
        db.close()


# 📥 Download CSV with Results
@router.get("/download_csv")
def download_csv(request_id: str):
    db = SessionLocal()
    try:
        request = db.query(ProcessingRequest).filter_by(request_id=request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Request ID not found")

        images = db.query(ImageData).filter_by(request_id=request_id).all()

        # Group by product
        grouped = {}
        for img in images:
            if img.product_name not in grouped:
                grouped[img.product_name] = {
                    "input_urls": [],
                    "output_urls": [],
                }
            grouped[img.product_name]["input_urls"].append(img.input_url)
            grouped[img.product_name]["output_urls"].append(img.output_url or "")

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["S. No.", "Product Name", "Input Image Urls", "Output Image Urls"])

        for i, (product_name, data) in enumerate(grouped.items(), start=1):
            clean_input_urls = " ".join([
                url.strip().replace('\n', '').replace('\r', '').replace(' ', '') 
                for url in data["input_urls"]
            ])
            clean_output_urls = " ".join([
                url.strip().replace('\n', '').replace('\r', '').replace(' ', '') 
                for url in data["output_urls"] if url
            ])

            writer.writerow([
                i,
                product_name,
                clean_input_urls,
                clean_output_urls
            ])

        output.seek(0)
        return StreamingResponse(output, media_type="text/csv", headers={
            "Content-Disposition": f"attachment; filename={request_id}_output.csv"
        })

    finally:
        db.close()
