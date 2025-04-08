from worker.celery_app import celery_app
from app.db.database import SessionLocal
from app.db.models import ImageData
import time

@celery_app.task
def process_image(image_id):
    db = SessionLocal()
    try:
        print(f"[TASK] Processing image ID: {image_id}")
        image = db.query(ImageData).filter(ImageData.id == image_id).first()
        if not image:
            print(f"[TASK] Image with ID {image_id} not found.")
            return

        time.sleep(2)  # Simulate processing

        input_urls = image.input_url.split()
        processed_urls = [url.replace("public", "processed") for url in input_urls]
        image.output_url = " ".join(processed_urls)
        image.status = "done"

        db.commit()  # ✅ This is critical
        print(f"[TASK] Image {image_id} processed and updated with output_url: {processed_urls}")
    except Exception as e:
        print(f"[TASK] Error processing image {image_id}: {e}")
    finally:
        db.close()
