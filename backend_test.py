#!/usr/bin/env python3

import requests
import sys
import json
import os
from datetime import datetime
from io import BytesIO
from PIL import Image

class LuminaGalleryTester:
    def __init__(self, base_url="https://pixelstore-api.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_images = []

    def create_test_image(self, color='red', size=(100, 100)):
        """Create a test image in memory"""
        img = Image.new('RGB', size, color=color)
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes

    def run_test(self, name, test_func):
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            success = test_func()
            if success:
                self.tests_passed += 1
                print(f"✅ Passed")
            else:
                print(f"❌ Failed")
            return success
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_root_endpoint(self):
        """Test root API endpoint"""
        response = requests.get(f"{self.api_url}/")
        if response.status_code == 200:
            data = response.json()
            return data.get("message") == "Lumina Gallery API"
        return False

    def test_upload_image(self):
        """Test image upload with metadata"""
        img_bytes = self.create_test_image()
        
        files = {"file": ("test_image.png", img_bytes, "image/png")}
        data = {
            "uploader": "Test User",
            "tags": "test, nature, landscape",
            "description": "A test image for API testing"
        }
        
        response = requests.post(f"{self.api_url}/images/upload", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            # Store for cleanup
            self.uploaded_images.append(result["id"])
            
            # Validate response structure
            required_fields = ["id", "filename", "uploader", "tags", "description", "url"]
            if all(field in result for field in required_fields):
                return (result["uploader"] == "Test User" and 
                       "test" in result["tags"] and 
                       result["description"] == "A test image for API testing")
        return False

    def test_upload_invalid_file(self):
        """Test upload with non-image file"""
        files = {"file": ("test.txt", BytesIO(b"not an image"), "text/plain")}
        data = {"uploader": "Test User"}
        
        response = requests.post(f"{self.api_url}/images/upload", files=files, data=data)
        return response.status_code == 400

    def test_list_images(self):
        """Test listing all images"""
        response = requests.get(f"{self.api_url}/images")
        
        if response.status_code == 200:
            images = response.json()
            return isinstance(images, list)
        return False

    def test_filter_by_uploader(self):
        """Test filtering images by uploader"""
        # Upload a test image first
        img_bytes = self.create_test_image(color='blue')
        files = {"file": ("filter_test.png", img_bytes, "image/png")}
        data = {"uploader": "Filter Test User"}
        
        upload_response = requests.post(f"{self.api_url}/images/upload", files=files, data=data)
        if upload_response.status_code != 200:
            return False
            
        image_id = upload_response.json()["id"]
        self.uploaded_images.append(image_id)
        
        # Filter by uploader
        response = requests.get(f"{self.api_url}/images?uploader=Filter Test User")
        
        if response.status_code == 200:
            images = response.json()
            return len(images) >= 1 and all(img["uploader"] == "Filter Test User" for img in images)
        return False

    def test_filter_by_tags(self):
        """Test filtering images by tags"""
        # Upload image with specific tags
        img_bytes = self.create_test_image(color='green')
        files = {"file": ("tag_test.png", img_bytes, "image/png")}
        data = {"uploader": "Tag Test User", "tags": "nature, forest, green"}
        
        upload_response = requests.post(f"{self.api_url}/images/upload", files=files, data=data)
        if upload_response.status_code != 200:
            return False
            
        image_id = upload_response.json()["id"]
        self.uploaded_images.append(image_id)
        
        # Filter by tag
        response = requests.get(f"{self.api_url}/images?tags=nature")
        
        if response.status_code == 200:
            images = response.json()
            return len(images) >= 1 and any("nature" in img["tags"] for img in images)
        return False

    def test_get_image_metadata(self):
        """Test getting metadata for a specific image"""
        if not self.uploaded_images:
            return False
            
        image_id = self.uploaded_images[0]
        response = requests.get(f"{self.api_url}/images/{image_id}")
        
        if response.status_code == 200:
            data = response.json()
            return data["id"] == image_id
        return False

    def test_get_nonexistent_image(self):
        """Test getting a non-existent image"""
        response = requests.get(f"{self.api_url}/images/nonexistent-id")
        return response.status_code == 404

    def test_download_image(self):
        """Test downloading an image file"""
        if not self.uploaded_images:
            return False
            
        image_id = self.uploaded_images[0]
        response = requests.get(f"{self.api_url}/images/{image_id}/file")
        
        if response.status_code == 200:
            return (response.headers.get("content-type", "").startswith("image/") and 
                   len(response.content) > 0)
        return False

    def test_delete_image(self):
        """Test deleting an image"""
        if not self.uploaded_images:
            return False
            
        image_id = self.uploaded_images.pop()  # Remove from list as we're deleting it
        response = requests.delete(f"{self.api_url}/images/{image_id}")
        
        if response.status_code == 200:
            # Verify it's deleted
            get_response = requests.get(f"{self.api_url}/images/{image_id}")
            return get_response.status_code == 404
        return False

    def test_delete_nonexistent_image(self):
        """Test deleting a non-existent image"""
        response = requests.delete(f"{self.api_url}/images/nonexistent-id")
        return response.status_code == 404

    def cleanup(self):
        """Clean up uploaded test images"""
        print(f"\n🧹 Cleaning up {len(self.uploaded_images)} test images...")
        for image_id in self.uploaded_images:
            try:
                requests.delete(f"{self.api_url}/images/{image_id}")
            except:
                pass

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting Lumina Gallery Backend API Tests")
        print(f"📍 Testing against: {self.base_url}")
        
        # Test cases
        tests = [
            ("Root Endpoint", self.test_root_endpoint),
            ("Upload Image", self.test_upload_image),
            ("Upload Invalid File", self.test_upload_invalid_file),
            ("List Images", self.test_list_images),
            ("Filter by Uploader", self.test_filter_by_uploader),
            ("Filter by Tags", self.test_filter_by_tags),
            ("Get Image Metadata", self.test_get_image_metadata),
            ("Get Nonexistent Image", self.test_get_nonexistent_image),
            ("Download Image", self.test_download_image),
            ("Delete Image", self.test_delete_image),
            ("Delete Nonexistent Image", self.test_delete_nonexistent_image),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Cleanup
        self.cleanup()
        
        # Print results
        print(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = LuminaGalleryTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())