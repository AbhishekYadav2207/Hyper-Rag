import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_file_upload():
    """Test file upload."""
    print("=== Test File Upload ===")
    
    # Create a test file
    test_file_content = """
    This is a test document used to verify file upload and parsing functionality.
    
    # Test Title
    
    This document contains basic text content to test HyperRAG's document processing capabilities.
    
    ## Test Content
    
    1. Text parsing test
    2. Document embedding test
    3. Query functionality test
    
    This is a complete testing workflow.
    """
    
    # Save as temporary file
    test_file_path = "test_document.txt"
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_file_content)
    
    try:
        # Upload file
        with open(test_file_path, 'rb') as f:
            files = {'files': (test_file_path, f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/files/upload", files=files)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        # Return uploaded file info
        if response.status_code == 200:
            files_data = response.json().get('files', [])
            if files_data:
                return files_data[0].get('file_id')
    
    finally:
        # Clean up temporary file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    
    return None

def test_get_files():
    """Test retrieving file list."""
    print("\n=== Test Get Files List ===")
    response = requests.get(f"{BASE_URL}/files")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()

def test_embed_files(file_ids):
    """Test embedding files."""
    print(f"\n=== Test Embedding Files: {file_ids} ===")
    
    data = {
        "file_ids": file_ids,
        "database_name": "test_db",
        "chunk_size": 1200,
        "chunk_overlap": 100
    }
    
    response = requests.post(f"{BASE_URL}/files/embed", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()

def test_delete_file(file_id):
    """Test deleting file."""
    print(f"\n=== Test Delete File: {file_id} ===")
    response = requests.delete(f"{BASE_URL}/files/{file_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()

def main():
    """Main test workflow."""
    print("Starting file management API tests...")
    
    # 1. Test upload
    file_id = test_file_upload()
    
    if not file_id:
        print("[FAILED] Upload failed, aborting remaining tests")
        return
    
    # 2. Test get files list
    test_get_files()
    
    # 3. Test embed
    # test_embed_files([file_id])
    
    # 4. Wait for processing
    # time.sleep(2)
    
    # 5. Check status again
    # test_get_files()
    
    # 6. Test delete
    test_delete_file(file_id)
    
    # 7. Confirm deletion
    test_get_files()
    
    print("\nFile management API tests completed!")

if __name__ == "__main__":
    main()