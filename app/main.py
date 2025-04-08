from fastapi import FastAPI
from app.routes.api import router  # or from app.routes.api import router if your router is there

app = FastAPI()

# Include your API router only once
app.include_router(router)

