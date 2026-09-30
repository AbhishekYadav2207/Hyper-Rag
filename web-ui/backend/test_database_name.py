#!/usr/bin/env python3
"""
Test database name generation using first 5 characters of filename during upload.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add current directory to sys.path
sys.path.append(str(Path(__file__).parent))

from file_manager import FileManager


async def test_database_name_generation():
    """Test database name generation functionality"""
    print("Starting database name generation test...")
    
    # Create temporary directory as storage directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create FileManager instance
        metadata_file = os.path.join(temp_dir, "test_metadata.json")
        storage_dir = os.path.join(temp_dir, "uploads")
        file_manager = FileManager(storage_dir=storage_dir, metadata_file=metadata_file)
        
        # Test cases
        test_cases = [
            ("hello_world.txt", "hello"),
            ("test_doc.pdf", "test_"),
            ("AI-Report-2024.docx", "AIRep"),
            ("123ABC.txt", "123AB"),
            ("a.txt", "a"),
            ("@#$%^.txt", "default"),  # Special characters cleaned, default used
            ("user_manual_v1.0.md", "user_"),
            ("Python_Guide.pdf", "Pytho"),
            ("report-final-version.txt", "repor"),
            ("sample_test_doc_123.docx", "sampl"),
        ]
        
        print("\nTesting filename to database name mapping:")
        print("-" * 50)
        
        for filename, expected_db_name in test_cases:
            # Generate database name
            actual_db_name = file_manager.generate_database_name(filename)
            
            # Display results
            status = "PASS" if actual_db_name == expected_db_name else "FAIL"
            print(f"[{status}] {filename:25} -> {actual_db_name:8} (expected: {expected_db_name})")
            
            if actual_db_name != expected_db_name:
                print(f"   Error: expected '{expected_db_name}', got '{actual_db_name}'")
        
        print("\n" + "-" * 50)
        
        # Test file upload
        print("\nTesting file upload functionality:")
        test_files = [
            ("hello_world.txt", "Hello, World! This is a test file."),
            ("test_doc.txt", "This is an English test document."),
            ("AIReport.pdf", "This is an AI report content."),
        ]
        
        for filename, content in test_files:
            try:
                # Simulate file upload
                file_content = content.encode('utf-8')
                result = await file_manager.save_uploaded_file(file_content, filename)
                
                print(f"[PASS] Uploaded successfully: {filename}")
                print(f"  File ID: {result['file_id']}")
                print(f"  Database Name: {result['database_name']}")
                print(f"  File Size: {result['file_size']} bytes")
                print()
                
            except Exception as e:
                print(f"[FAIL] Upload failed: {filename} - {str(e)}")
        
        # Retrieve all files
        all_files = file_manager.get_all_files()
        print("All uploaded files:")
        print("-" * 70)
        print(f"{'Filename':20} {'Database':10} {'Size':8} {'Status':8}")
        print("-" * 70)
        
        for file_info in all_files:
            print(f"{file_info['filename']:20} {file_info['database_name']:10} {file_info['file_size']:8} {file_info['status']:8}")
        
        print(f"\nTest finished! Total uploaded: {len(all_files)} files")


if __name__ == "__main__":
    asyncio.run(test_database_name_generation()) 