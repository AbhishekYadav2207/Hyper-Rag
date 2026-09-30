import os
import uuid
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import aiofiles
import asyncio

class FileManager:
    def __init__(
        self,
        storage_dir: str = "uploads",
        metadata_file: str = "file_metadata.json",
        db_path: Optional[str] = None,
    ):
        if db_path is not None:
            metadata_file = db_path
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Metadata file path
        self.metadata_file = Path(metadata_file)
        self.metadata_lock = asyncio.Lock()
        
        # Supported file types
        self.supported_extensions = {'.txt', '.pdf', '.docx', '.md', '.doc'}
        self.supported_mime_types = {
            'text/plain', 'application/pdf', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword', 'text/markdown'
        }
        
        # Initialize metadata file
        self._init_metadata_file()
    
    def _init_metadata_file(self):
        """Initialize metadata file if not exists."""
        if not self.metadata_file.exists():
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _load_metadata(self) -> Dict:
        """Load metadata dictionary."""
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_metadata(self, metadata: Dict):
        """Save metadata dictionary."""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def generate_file_id(self) -> str:
        """Generate unique file ID."""
        return str(uuid.uuid4())
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def is_supported_file(self, filename: str, mime_type: str = None) -> bool:
        """Check if file type is supported."""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_extensions or (mime_type and mime_type in self.supported_mime_types)
    
    def generate_database_name(self, filename: str) -> str:
        """Generate database name using first 5 valid characters of filename."""
        name_without_ext = Path(filename).stem
        clean_name = re.sub(r'[^\w]', '', name_without_ext)
        db_name = clean_name[:5]
        if len(db_name) < 1:
            db_name = "default"
        return db_name
    
    async def save_uploaded_file(self, file_content: bytes, original_filename: str) -> Dict:
        """Save uploaded file and record metadata."""
        try:
            ext = Path(original_filename).suffix.lower()
            mime_type_map = {
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword',
                '.md': 'text/markdown'
            }
            mime_type = mime_type_map.get(ext, 'application/octet-stream')
            
            if not self.is_supported_file(original_filename, mime_type):
                raise ValueError(f"Unsupported file type: {original_filename}")
            
            database_name = self.generate_database_name(original_filename)
            
            file_id = self.generate_file_id()
            file_ext = Path(original_filename).suffix
            filename = f"{file_id}{file_ext}"
            file_path = self.storage_dir / filename
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            file_size = len(file_content)
            file_hash = self.get_file_hash(str(file_path))
            
            async with self.metadata_lock:
                metadata = self._load_metadata()
                
                file_record = {
                    "file_id": file_id,
                    "filename": filename,
                    "original_filename": original_filename,
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "file_type": file_ext,
                    "mime_type": mime_type,
                    "database_name": database_name,
                    "upload_time": datetime.utcnow().isoformat(),
                    "status": "uploaded",
                    "processed_time": None,
                    "error_message": None,
                    "file_metadata": {"hash": file_hash}
                }
                
                metadata[file_id] = file_record
                self._save_metadata(metadata)
                
                return {
                    "file_id": file_id,
                    "filename": original_filename,
                    "file_path": str(file_path),
                    "database_name": database_name,
                    "file_size": file_size,
                    "status": "uploaded",
                    "upload_time": file_record["upload_time"]
                }
                
        except Exception as e:
            if 'file_path' in locals() and file_path.exists():
                file_path.unlink()
            raise e
    
    def get_all_files(self) -> List[Dict]:
        """Get list of all uploaded files."""
        metadata = self._load_metadata()
        files = []
        
        for file_id, file_record in metadata.items():
            files.append({
                "file_id": file_record["file_id"],
                "filename": file_record["original_filename"],
                "database_name": file_record["database_name"],
                "file_size": file_record["file_size"],
                "file_type": file_record["file_type"],
                "mime_type": file_record["mime_type"],
                "upload_time": file_record["upload_time"],
                "status": file_record["status"],
                "processed_time": file_record.get("processed_time"),
                "error_message": file_record.get("error_message")
            })
        
        files.sort(key=lambda x: x["upload_time"], reverse=True)
        return files
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        """Get file info by ID."""
        metadata = self._load_metadata()
        file_record = metadata.get(file_id)
        
        if not file_record:
            return None
        
        return {
            "file_id": file_record["file_id"],
            "filename": file_record["original_filename"],
            "database_name": file_record["database_name"],
            "file_path": file_record["file_path"],
            "file_size": file_record["file_size"],
            "file_type": file_record["file_type"],
            "mime_type": file_record["mime_type"],
            "upload_time": file_record["upload_time"],
            "status": file_record["status"],
            "processed_time": file_record.get("processed_time"),
            "error_message": file_record.get("error_message")
        }
    
    def update_file_status(self, file_id: str, status: str, error_message: str = None):
        """Update status of a file."""
        metadata = self._load_metadata()
        
        if file_id in metadata:
            metadata[file_id]["status"] = status
            if error_message:
                metadata[file_id]["error_message"] = error_message
            if status == "embedded":
                metadata[file_id]["processed_time"] = datetime.utcnow().isoformat()
            
            self._save_metadata(metadata)
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file and its metadata."""
        metadata = self._load_metadata()
        
        if file_id not in metadata:
            return False
        
        file_record = metadata[file_id]
        
        file_path = Path(file_record["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        del metadata[file_id]
        self._save_metadata(metadata)
        
        return True
    
    async def read_file_content(self, file_path: str) -> str:
        """Read text content from file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.suffix.lower() == '.pdf':
            return self._read_pdf(file_path)
        elif file_path.suffix.lower() in ['.docx']:
            return self._read_docx(file_path)
        elif file_path.suffix.lower() in ['.txt', '.md']:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
    
    def _read_pdf(self, file_path: Path) -> str:
        """Read PDF file content."""
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            raise ValueError(f"Failed to read PDF file: {str(e)}")
    
    def _read_docx(self, file_path: Path) -> str:
        """Read DOCX file content."""
        try:
            import docx2txt
            return docx2txt.process(str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to read DOCX file: {str(e)}")

# Global file manager instance
file_manager = FileManager()