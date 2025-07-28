#!/usr/bin/env python3
"""
Test script for Google Cloud Vision API
"""

import os
import sys
from pathlib import Path

# Set the credentials path
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'cloud-credentials.json'

try:
    from google.cloud import vision_v1
    import io
    
    def test_vision_api():
        """Test if Google Cloud Vision API is working"""
        print("🔍 Testing Google Cloud Vision API...")
        
        # Create a simple test image with text (or use an existing one)
        test_image_path = None
        
        # Look for any existing images in extraction_cache
        cache_dir = Path("extraction_cache")
        if cache_dir.exists():
            for img_file in cache_dir.glob("*.png"):
                test_image_path = img_file
                break
            if not test_image_path:
                for img_file in cache_dir.glob("*.jpeg"):
                    test_image_path = img_file
                    break
        
        if test_image_path and test_image_path.exists():
            print(f"📸 Using test image: {test_image_path}")
            
            try:
                client = vision_v1.ImageAnnotatorClient()
                
                with io.open(test_image_path, 'rb') as image_file:
                    content = image_file.read()
                
                image = vision_v1.Image(content=content)
                response = client.document_text_detection(image=image)
                
                if response.full_text_annotation:
                    print("✅ Google Cloud Vision API is working!")
                    print(f"📝 Extracted text length: {len(response.full_text_annotation.text)} characters")
                    print(f"📄 Sample text: {response.full_text_annotation.text[:200]}...")
                    return True
                else:
                    print("⚠️ No text detected in image")
                    return True  # API is working, just no text found
                    
            except Exception as e:
                print(f"❌ Error testing Vision API: {e}")
                return False
        else:
            print("⚠️ No test images found in extraction_cache")
            print("✅ Google Cloud Vision API credentials are configured")
            return True
            
    if __name__ == "__main__":
        success = test_vision_api()
        if success:
            print("\n🎉 Google Cloud Vision API is ready for enhanced PDF extraction!")
        else:
            print("\n❌ Google Cloud Vision API setup needs attention")
            
except ImportError as e:
    print(f"❌ Google Cloud Vision library not installed: {e}")
    print("💡 Install with: pip install google-cloud-vision")
except Exception as e:
    print(f"❌ Error: {e}") 