#!/usr/bin/env python3
"""
HyperRAG API Test Script

This script demonstrates how to query the HyperRAG QA API endpoints.
Ensure before running:
1. Start backend server: uvicorn main:app --reload
2. Configure appropriate API keys and settings in settings.json
"""

import requests
import json
import time
from pathlib import Path

# API Base URL
BASE_URL = "http://localhost:8000"

def test_hyperrag_status():
    """Test HyperRAG status endpoint."""
    print("=== Test HyperRAG Status ===")
    response = requests.get(f"{BASE_URL}/hyperrag/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_insert_document():
    """Test document insertion."""
    print("=== Test Document Insertion ===")
    
    sample_path = Path("./public/sample.txt")
    if sample_path.exists():
        document_content = open(sample_path, "r", encoding="utf-8").read()
    else:
        document_content = "This is a sample document for HyperRAG testing."
    
    data = {
        "content": document_content,
        "retries": 3,
        "database": "sample"
    }
    
    response = requests.post(f"{BASE_URL}/hyperrag/insert", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_query_hyperrag(question, database, mode="adaptive"):
    """Test question-answering query."""
    print(f"=== Test HyperRAG Query ({mode}) ===")
    print(f"Question: {question}")
    
    data = {
        "question": question,
        "mode": mode,
        "top_k": 60,
        "max_token_for_text_unit": 1600,
        "max_token_for_entity_context": 300,
        "max_token_for_relation_context": 1600,
        "only_need_context": False,
        "response_type": "Multiple Paragraphs",
        "database": database
    }   
    
    response = requests.post(f"{BASE_URL}/hyperrag/query", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response}")
    result = response.json()
    print(f"Success: {result.get('success', False)}")
    
    if result.get('success'):
        print(f"Answer: {result.get('response', 'No response')}")
        if result.get('adaptive_decision'):
            print(f"Adaptive Decision: {result.get('adaptive_decision')}")
    else:
        print(f"Error: {result.get('message', 'Unknown error')}")
    print()

def test_settings():
    """Test settings endpoint."""
    print("=== Test Settings Endpoint ===")
    response = requests.get(f"{BASE_URL}/settings")
    print(f"Status: {response.status_code}")
    print(f"Settings: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_get_databases():
    """Test retrieving available databases."""
    print("=== Test Get Available Databases ===")
    response = requests.get(f"{BASE_URL}/databases")
    print(f"Status: {response.status_code}")
    print(f"Databases: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def main():
    """Main test workflow."""
    print("Starting HyperRAG API tests...")
    print()

    # Get available databases
    test_get_databases()
    
    # Test status
    test_hyperrag_status()

    # Test settings
    test_settings()
    
    test_questions = [
        "What are the central themes discussed in the knowledge base?"
    ]
    
    for question in test_questions:
        test_query_hyperrag(question, "default", "adaptive")
        test_query_hyperrag(question, "default", "hyper")
        test_query_hyperrag(question, "default", "hyper-lite")
    
    print("Tests completed!")

if __name__ == "__main__":
    main()