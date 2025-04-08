from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ProcessingRequest(Base):
    __tablename__ = 'processing_requests'

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class ImageData(Base):
    __tablename__ = 'images'

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("processing_requests.request_id"))
    serial_number = Column(Integer, index=True)
    product_name = Column(String)
    input_url = Column(String)
    output_url = Column(String, nullable=True)
    status = Column(String, default="pending")
