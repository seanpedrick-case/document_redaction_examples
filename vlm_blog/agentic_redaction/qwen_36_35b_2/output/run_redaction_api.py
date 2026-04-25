#!/usr/bin/env python3
"""Use direct HTTP requests to call the Document Redaction Gradio API."""

import json, os, time, hashlib, uuid, io

import requests

base = "https://seanpedrickcase-document-redaction.hf.space" 
pdf_path = "/home/spedrickcase/Partnership-Agreement-Toolkit_0_0.pdf"
output_dir = "/home/spedrickcase/output/gradio_output"
os.makedirs(output_dir, exist_ok=True)

session = requests.Session()

# Step 1: Upload the PDF file to Gradio's upload endpoint  
print("Step 1: Uploading PDF...") 
upload_url = f"{base}/gradio_api/upload"

with open(pdf_path, 'rb') as f:
    files = {
        'files': (os.path.basename(pdf_path), f, 'application/pdf'),
    }
    
    # For Gradio v6 SSE protocol, we need to include an upload_id  
    session.headers.update({
        'Origin': base, 
        'Referer': f'{base}/',
    }) 
    
    resp = session.post(upload_url, files=files) 
print(f"Upload response: {resp.status_code}") 

try:
    upload_data = resp.json() if resp.content else {}
except:
    upload_data = {'error': resp.text[:200] if resp.text else 'no content'}

print(f"Upload data keys: {list(upload_data.keys()) if isinstance(upload_data, dict) else type(upload_data)}") 
if isinstance(upload_data, dict):
    for k, v in upload_data.items():
        print(f"  {k}: {str(v)[:200]}")

# Step 2: Now call predict with the uploaded file reference  
print("\nStep 2: Calling predict...") 

# Get session hash from cookies or response 
session_hash = None 
for cookie in session.cookies:
    if 'gradio' in cookie.name.lower() or 'session' in cookie.name.lower():
        session_hash = cookie.value
        print(f"Found session cookie: {cookie.name}={cookie.value[:20]}")

# Try calling predict endpoint  
predict_url = f"{base}/gradio_api/api/predict/" 

# Build the request payload for prepare_image_or_pdf_with_efficient_ocr  
# This function needs 19 inputs in order:
# [0] file (uploaded), [1] radio (OCR method), [2-4] states, [5] textbox, 
#     [6] checkbox, [7] number, [8-9] states/checkboxes, 
#     etc.

payload = {
    "data": None,  # Will be set below  
    "session_hash": session_hash or "test-session",
}

# Let's first try a simple test to see what format is expected  
print(f"\nTrying predict call...") 

# For Gradio v6 with SSE, we need to send data through the queue endpoint
queue_url = f"{base}/gradio_api/queue/data"

# Try POST to predict URL directly 
test_payload = {
    "data": [],  # Empty - let's see what format is expected  
}

try:
    resp = session.post(predict_url, json=test_payload, timeout=30) 
    print(f"\nPredict (empty data): {resp.status_code}")
    if resp.text and len(resp.text) < 500:
        print(f"Response: {resp.text[:400]}")
except Exception as e:
    print(f"Predict error: {e}")

# Try with SSE queue endpoint  
print(f"\nTrying queue/data endpoint...") 
try:
    resp = session.post(queue_url, json=test_payload, timeout=30) 
    print(f"Queue POST: {resp.status_code}")
    if resp.text and len(resp.text) < 500:
        print(f"Response: {resp.text[:400]}")
except Exception as e:
    print(f"Queue error: {e}")

print("\nDone with initial exploration.")
