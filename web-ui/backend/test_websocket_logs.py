import asyncio
import websockets
import json
import requests
import tempfile
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

async def test_websocket_logs():
    """Test WebSocket logging functionality."""
    print("=== Test WebSocket Logging ===")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("[OK] WebSocket connected successfully")
            
            test_content = """
            This is a test document used to verify WebSocket logging functionality.
            
            # HyperRAG Logging Test
            
            This document will be uploaded and embedded into the HyperRAG system.
            Detailed processing logs are emitted during execution.
            
            ## Test Sections
            
            1. Document upload test
            2. Document parsing test
            3. Document embedding test
            4. WebSocket log transmission test
            """
            
            test_file_path = "websocket_test.txt"
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            try:
                # 1. Upload file
                print("\n1. Uploading test file...")
                with open(test_file_path, 'rb') as f:
                    files = {'files': (test_file_path, f, 'text/plain')}
                    response = requests.post(f"{BASE_URL}/files/upload", files=files)
                
                if response.status_code != 200:
                    print(f"[ERROR] File upload failed: {response.text}")
                    return
                
                files_data = response.json().get('files', [])
                if not files_data:
                    print("[ERROR] No file info received from upload response")
                    return
                
                file_id = files_data[0].get('file_id')
                print(f"[OK] File uploaded successfully, ID: {file_id}")
                
                # 2. Trigger embed and listen to logs
                print("\n2. Triggering document embedding and listening to logs...")
                embed_data = {
                    "file_ids": [file_id],
                    "chunk_size": 500,
                    "chunk_overlap": 100
                }
                
                response = requests.post(f"{BASE_URL}/files/embed-with-progress", json=embed_data)
                if response.status_code != 200:
                    print(f"[ERROR] Embedding trigger failed: {response.text}")
                    return
                
                print("[OK] Embedding initiated, listening to WebSocket stream...")
                
                # 3. Listen for WebSocket messages
                log_count = 0
                progress_count = 0
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get('type', 'unknown')
                        
                        if msg_type == 'log':
                            log_count += 1
                            timestamp = data.get('timestamp', 0)
                            level = data.get('level', 'INFO')
                            log_message = data.get('message', '')
                            
                            print(f"[LOG] [{level}] {log_message}")
                            
                        elif msg_type == 'progress':
                            progress_count += 1
                            current = data.get('current', 0)
                            total = data.get('total', 0)
                            percentage = data.get('percentage', 0)
                            prog_message = data.get('message', '')
                            
                            print(f"[PROGRESS] {current}/{total} ({percentage:.1f}%) - {prog_message}")
                            
                        elif msg_type == 'file_processing':
                            filename = data.get('filename', '')
                            stage = data.get('stage', '')
                            proc_message = data.get('message', '')
                            print(f"[PROCESSING] {filename} - {stage} - {proc_message}")
                            
                        elif msg_type == 'file_completed':
                            filename = data.get('filename', '')
                            print(f"[OK] Completed: {filename}")
                            
                        elif msg_type == 'all_completed':
                            print("[SUCCESS] All documents processed successfully!")
                            break
                            
                        elif msg_type == 'error' or msg_type == 'file_error':
                            error = data.get('error', 'Unknown error')
                            print(f"[ERROR] {error}")
                            break
                            
                    except json.JSONDecodeError:
                        print(f"[WARN] Received non-JSON message: {message}")
                
                print("\n[SUMMARY] Statistics:")
                print(f"   - Received log messages: {log_count}")
                print(f"   - Received progress messages: {progress_count}")
                
                # 4. Clean up test file
                print("\n4. Cleaning up test file...")
                delete_response = requests.delete(f"{BASE_URL}/files/{file_id}")
                if delete_response.status_code == 200:
                    print("[OK] Test file deleted successfully")
                else:
                    print(f"[WARN] Test file deletion failed: {delete_response.text}")
                
            finally:
                if os.path.exists(test_file_path):
                    os.remove(test_file_path)
            
    except Exception as e:
        print(f"[ERROR] Test failed: {str(e)}")

def main():
    """Main function."""
    print("Starting WebSocket logging test...")
    print("Ensure backend service is running (uvicorn main:app --reload)")
    
    try:
        asyncio.run(test_websocket_logs())
        print("\nWebSocket logging test completed!")
    except KeyboardInterrupt:
        print("\n[WARN] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")

if __name__ == "__main__":
    main()