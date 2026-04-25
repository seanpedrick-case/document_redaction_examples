#!/usr/bin/env python3  
"""Direct HTTP calls to Gradio API for document redaction."""

import json, os, time, uuid

import requests

base = "https://seanpedrickcase-document-redaction.hf.space" 
pdf_path = "/home/spedrickcase/Partnership-Agreement-Toolkit_0_0.pdf"
output_dir = "/home/spedrickcase/output/gradio_output"
os.makedirs(output_dir, exist_ok=True)

session = requests.Session()
session.headers.update({
    'Origin': base, 
    'Referer': f'{base}/', 
})

# Step 1: Upload the PDF file  
print("Step 1: Uploading PDF...")  
upload_url = f"{base}/gradio_api/upload" 

with open(pdf_path, 'rb') as f:
    files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
    resp = session.post(upload_url, files=files)

print(f"Upload status: {resp.status_code}") 
upload_data = resp.json() if resp.content else {}  
print(f"Upload response keys: {list(upload_data.keys()) if isinstance(upload_data, dict) else type(upload_data)}") 

# Extract file references from upload response  
uploaded_files = []
if isinstance(upload_data, dict):
    # Gradio v4+ returns list of uploaded files 
    for key in ['files', 'file_paths']: 
        if key in upload_data:
            uploaded_files = upload_data[key] if isinstance(upload_data[key], list) else [upload_data[key]]  
            break
    
    # Also check the response structure more carefully  
    print(f"Upload data: {json.dumps(upload_data, indent=2)[:500]}")

# Step 2: Get session ID from cookie or create one 
session_id = None
for cookie in session.cookies:
    if 'gradio' in cookie.name.lower():
        session_id = cookie.value  
        break 

if not session_id:
    # Try to get it from the response headers  
    for header, value in resp.headers.items():
        if 'set-cookie' in header.lower() and 'gradio' in value.lower(): 
            # Extract session ID from Set-Cookie header 
            import re 
            match = re.search(r'session_id=([a-zA-Z0-9_-]+)', value)  
            if match:
                session_id = match.group(1)

print(f"Session ID: {session_id or 'not found'}") 

# Step 3: Call predict endpoint with proper SSE format  
predict_url = f"{base}/gradio_api/api/predict/"  

# Build the request payload for prepare_image_or_pdf_with_efficient_ocr (fn_index=15)
# The gradio_client sends data in a specific JSON format

payload = {
    "data": None,  # Will be set below 
}

print(f"\nStep 2: Calling predict...") 

# First try with just the file to see what format is expected  
test_payload = {
    "data": [], 
}

try:
    resp = session.post(predict_url, json=test_payload, timeout=30)  
    print(f"Predict (empty): {resp.status_code}") 
except Exception as e:
    print(f"Error: {e}")

print("\nDone with initial exploration.") 
