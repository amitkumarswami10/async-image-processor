from app.db.models import Base
from app.db.database import engine

# This will create tables defined in models.py
Base.metadata.create_all(bind=engine)

print("✅ Database tables created.")