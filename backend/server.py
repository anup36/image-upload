from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import shutil
import mimetypes


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)

# Create the main app without a prefix
app = FastAPI(title="Lumina Gallery API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class ImageMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_size: int
    file_type: str
    uploader: str
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    filename: str
    file_size: int
    file_type: str
    uploader: str
    tags: List[str]
    description: Optional[str]
    upload_date: str
    url: str


@api_router.get("/")
async def root():
    return {"message": "Lumina Gallery API", "version": "1.0.0"}


@api_router.post("/images/upload", response_model=ImageResponse)
async def upload_image(
    file: UploadFile = File(...),
    uploader: str = Form(...),
    tags: str = Form(""),
    description: Optional[str] = Form(None)
):
    """
    Upload an image with metadata.
    Tags should be comma-separated string.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOADS_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Get file size
    file_size = file_path.stat().st_size
    
    # Parse tags
    tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    # Create metadata
    metadata = ImageMetadata(
        filename=file.filename,
        file_size=file_size,
        file_type=file.content_type,
        uploader=uploader,
        tags=tags_list,
        description=description
    )
    
    # Save to database
    doc = metadata.model_dump()
    doc['upload_date'] = doc['upload_date'].isoformat()
    doc['file_path'] = str(file_path)
    
    await db.images.insert_one(doc)
    
    # Return response
    return ImageResponse(
        id=metadata.id,
        filename=metadata.filename,
        file_size=metadata.file_size,
        file_type=metadata.file_type,
        uploader=metadata.uploader,
        tags=metadata.tags,
        description=metadata.description,
        upload_date=metadata.upload_date.isoformat(),
        url=f"/api/images/{metadata.id}/file"
    )


@api_router.get("/images", response_model=List[ImageResponse])
async def list_images(
    date_from: Optional[str] = Query(None, description="ISO format date string"),
    date_to: Optional[str] = Query(None, description="ISO format date string"),
    uploader: Optional[str] = Query(None, description="Filter by uploader name"),
    tags: Optional[str] = Query(None, description="Comma-separated tags")
):
    """
    List all images with optional filters.
    Supports filtering by date range, uploader, and tags.
    """
    query = {}
    
    # Date range filter
    if date_from or date_to:
        date_query = {}
        if date_from:
            try:
                date_query['$gte'] = datetime.fromisoformat(date_from).isoformat()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO format.")
        if date_to:
            try:
                date_query['$lte'] = datetime.fromisoformat(date_to).isoformat()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO format.")
        query['upload_date'] = date_query
    
    # Uploader filter
    if uploader:
        query['uploader'] = uploader
    
    # Tags filter
    if tags:
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        query['tags'] = {'$in': tags_list}
    
    # Fetch from database
    images = await db.images.find(query, {"_id": 0}).sort("upload_date", -1).to_list(1000)
    
    # Convert to response format
    response = []
    for img in images:
        response.append(ImageResponse(
            id=img['id'],
            filename=img['filename'],
            file_size=img['file_size'],
            file_type=img['file_type'],
            uploader=img['uploader'],
            tags=img['tags'],
            description=img.get('description'),
            upload_date=img['upload_date'],
            url=f"/api/images/{img['id']}/file"
        ))
    
    return response


@api_router.get("/images/{image_id}", response_model=ImageResponse)
async def get_image(image_id: str):
    """
    Get metadata for a specific image.
    """
    image = await db.images.find_one({"id": image_id}, {"_id": 0})
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return ImageResponse(
        id=image['id'],
        filename=image['filename'],
        file_size=image['file_size'],
        file_type=image['file_type'],
        uploader=image['uploader'],
        tags=image['tags'],
        description=image.get('description'),
        upload_date=image['upload_date'],
        url=f"/api/images/{image['id']}/file"
    )


@api_router.get("/images/{image_id}/file")
async def download_image(image_id: str):
    """
    Download or view the actual image file.
    """
    image = await db.images.find_one({"id": image_id}, {"_id": 0})
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path = Path(image['file_path'])
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")
    
    # Determine media type
    media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=image['filename']
    )


@api_router.delete("/images/{image_id}")
async def delete_image(image_id: str):
    """
    Delete an image and its file.
    """
    image = await db.images.find_one({"id": image_id}, {"_id": 0})
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete file from disk
    file_path = Path(image['file_path'])
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            logging.error(f"Failed to delete file {file_path}: {e}")
    
    # Delete from database
    result = await db.images.delete_one({"id": image_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete image from database")
    
    return {"message": "Image deleted successfully", "id": image_id}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()