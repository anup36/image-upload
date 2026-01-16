import pytest
import pytest_asyncio
import os
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from io import BytesIO
from PIL import Image

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from server import app, db, UPLOADS_DIR


@pytest_asyncio.fixture
async def client():
    """Create test client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # Cleanup: delete all test images
    await db.images.delete_many({})
    for file in UPLOADS_DIR.glob("*"):
        if file.is_file():
            file.unlink()


def create_test_image():
    """Create a test image in memory"""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint"""
    response = await client.get("/api/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Lumina Gallery API"


@pytest.mark.asyncio
async def test_upload_image(client):
    """Test image upload with metadata"""
    img_bytes = create_test_image()
    
    files = {"file": ("test_image.png", img_bytes, "image/png")}
    data = {
        "uploader": "Test User",
        "tags": "test, nature, landscape",
        "description": "A test image"
    }
    
    response = await client.post("/api/images/upload", files=files, data=data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["uploader"] == "Test User"
    assert "test" in result["tags"]
    assert "nature" in result["tags"]
    assert "landscape" in result["tags"]
    assert result["description"] == "A test image"
    assert "id" in result
    assert "url" in result


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client):
    """Test upload with non-image file"""
    files = {"file": ("test.txt", BytesIO(b"not an image"), "text/plain")}
    data = {"uploader": "Test User"}
    
    response = await client.post("/api/images/upload", files=files, data=data)
    assert response.status_code == 400
    assert "Only image files are allowed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_images(client):
    """Test listing all images"""
    # Upload a test image first
    img_bytes = create_test_image()
    files = {"file": ("test_image.png", img_bytes, "image/png")}
    data = {"uploader": "Test User", "tags": "test"}
    await client.post("/api/images/upload", files=files, data=data)
    
    # List images
    response = await client.get("/api/images")
    assert response.status_code == 200
    
    images = response.json()
    assert len(images) >= 1
    assert images[0]["uploader"] == "Test User"


@pytest.mark.asyncio
async def test_filter_by_uploader(client):
    """Test filtering images by uploader"""
    # Upload two images with different uploaders
    img_bytes1 = create_test_image()
    files1 = {"file": ("image1.png", img_bytes1, "image/png")}
    await client.post("/api/images/upload", files=files1, data={"uploader": "User1"})
    
    img_bytes2 = create_test_image()
    files2 = {"file": ("image2.png", img_bytes2, "image/png")}
    await client.post("/api/images/upload", files=files2, data={"uploader": "User2"})
    
    # Filter by User1
    response = await client.get("/api/images?uploader=User1")
    assert response.status_code == 200
    
    images = response.json()
    assert len(images) == 1
    assert images[0]["uploader"] == "User1"


@pytest.mark.asyncio
async def test_filter_by_tags(client):
    """Test filtering images by tags"""
    # Upload images with different tags
    img_bytes1 = create_test_image()
    files1 = {"file": ("nature.png", img_bytes1, "image/png")}
    await client.post("/api/images/upload", files=files1, data={"uploader": "User", "tags": "nature, landscape"})
    
    img_bytes2 = create_test_image()
    files2 = {"file": ("urban.png", img_bytes2, "image/png")}
    await client.post("/api/images/upload", files=files2, data={"uploader": "User", "tags": "urban, city"})
    
    # Filter by nature tag
    response = await client.get("/api/images?tags=nature")
    assert response.status_code == 200
    
    images = response.json()
    assert len(images) == 1
    assert "nature" in images[0]["tags"]


@pytest.mark.asyncio
async def test_filter_by_date_range(client):
    """Test filtering images by date range"""
    from datetime import datetime, timezone, timedelta
    
    # Upload an image
    img_bytes = create_test_image()
    files = {"file": ("test.png", img_bytes, "image/png")}
    upload_response = await client.post("/api/images/upload", files=files, data={"uploader": "User"})
    upload_data = upload_response.json()
    upload_date = datetime.fromisoformat(upload_data["upload_date"])
    
    # Filter with date range that includes the upload
    date_from = (upload_date - timedelta(days=1)).isoformat()
    date_to = (upload_date + timedelta(days=1)).isoformat()
    
    response = await client.get(f"/api/images?date_from={date_from}&date_to={date_to}")
    assert response.status_code == 200
    
    images = response.json()
    assert len(images) >= 1


@pytest.mark.asyncio
async def test_get_image_metadata(client):
    """Test getting metadata for a specific image"""
    # Upload an image
    img_bytes = create_test_image()
    files = {"file": ("test.png", img_bytes, "image/png")}
    upload_response = await client.post("/api/images/upload", files=files, data={"uploader": "User"})
    image_id = upload_response.json()["id"]
    
    # Get metadata
    response = await client.get(f"/api/images/{image_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == image_id
    assert data["uploader"] == "User"


@pytest.mark.asyncio
async def test_get_nonexistent_image(client):
    """Test getting a non-existent image"""
    response = await client.get("/api/images/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_image(client):
    """Test downloading an image file"""
    # Upload an image
    img_bytes = create_test_image()
    files = {"file": ("test.png", img_bytes, "image/png")}
    upload_response = await client.post("/api/images/upload", files=files, data={"uploader": "User"})
    image_id = upload_response.json()["id"]
    
    # Download the image
    response = await client.get(f"/api/images/{image_id}/file")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_delete_image(client):
    """Test deleting an image"""
    # Upload an image
    img_bytes = create_test_image()
    files = {"file": ("test.png", img_bytes, "image/png")}
    upload_response = await client.post("/api/images/upload", files=files, data={"uploader": "User"})
    image_id = upload_response.json()["id"]
    
    # Delete the image
    response = await client.delete(f"/api/images/{image_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"].lower()
    
    # Verify it's deleted
    get_response = await client.get(f"/api/images/{image_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_image(client):
    """Test deleting a non-existent image"""
    response = await client.delete("/api/images/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_without_tags(client):
    """Test uploading an image without tags"""
    img_bytes = create_test_image()
    files = {"file": ("test.png", img_bytes, "image/png")}
    data = {"uploader": "User"}
    
    response = await client.post("/api/images/upload", files=files, data=data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["tags"] == []


@pytest.mark.asyncio
async def test_upload_without_description(client):
    """Test uploading an image without description"""
    img_bytes = create_test_image()
    files = {"file": ("test.png", img_bytes, "image/png")}
    data = {"uploader": "User"}
    
    response = await client.post("/api/images/upload", files=files, data=data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["description"] is None


@pytest.mark.asyncio
async def test_multiple_tag_filter(client):
    """Test filtering with multiple tags"""
    # Upload image with multiple tags
    img_bytes = create_test_image()
    files = {"file": ("test.png", img_bytes, "image/png")}
    await client.post("/api/images/upload", files=files, data={"uploader": "User", "tags": "nature, landscape, mountain"})
    
    # Filter by multiple tags
    response = await client.get("/api/images?tags=landscape,mountain")
    assert response.status_code == 200
    
    images = response.json()
    assert len(images) >= 1


@pytest.mark.asyncio
async def test_empty_gallery(client):
    """Test listing images when gallery is empty"""
    response = await client.get("/api/images")
    assert response.status_code == 200
    assert response.json() == []