#!/usr/bin/env python3  
"""Direct SSE call to Gradio API for document redaction."""

import json, os, time

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
print(f"Upload response type: {type(upload_data).__name__}") 

if isinstance(upload_data, dict):
    print(f"Upload data keys: {list(upload_data.keys())}")
    for k, v in upload_data.items():
        print(f"  {k}: {str(v)[:200]}")

# Get session ID from cookies 
session_id = None  
for cookie in session.cookies:
    if 'gradio' in cookie.name.lower() or 'session' in cookie.name.lower(): 
        session_id = cookie.value  
        print(f"Found session cookie: {cookie.name}={cookie.value[:30]}")

if not session_id:
    import uuid 
    session_id = str(uuid.uuid4())
    print(f"Generated random session ID: {session_id}") 

# Step 2: Prepare prediction data for fn_index=15 (prepare_image_or_pdf_with_efficient_ocr)
print(f"\nStep 2: Preparing prediction...")

uploaded_file_ref = None 
if isinstance(upload_data, dict):
    if 'files' in upload_data and isinstance(upload_data['files'], list) and len(upload_data['files']) > 0:
        uploaded_file_ref = upload_data['files'][0]  
        print(f"Uploaded file ref: {str(uploaded_file_ref)[:200]}")

# Build data array - try passing everything as simple types that won't cause comparison issues
data_array = [] 

if uploaded_file_ref and isinstance(uploaded_file_ref, str):
    # Use the server-side file path  
    data_array.append({'path': uploaded_file_ref, 'meta': {'_type': 'gradio.FileData'}}) 
else:
    data_array.append([{'path': pdf_path, 'meta': {'_type': 'gradio.FileData'}}])

# Radio button - Local OCR model  
data_array.append('Local OCR model - PDFs without selectable text') 

# State variables (6): pass as empty strings
for _ in range(6):
    data_array.append('')

# Textbox inputs (3)
for _ in range(3): 
    data_array.append('') 

# Checkbox inputs (4)  
for _ in range(4):
    data_array.append(False)

# Number inputs (3) - pass as 0  
for _ in range(3):
    data_array.append(0) 

# Dropdown input
data_array.append('')  

print(f"Data array length: {len(data_array)}") 
print(f"Data array types: {[type(x).__name__ for x in data_array]}")

# Step 3: Send prediction request  
predict_url = f"{base}/gradio_api/api/predict/" 

payload = {
    "data": data_array, 
    "session_hash": session_id,
}

print(f"\nStep 3: Sending prediction...") 

try:
    resp = session.post(predict_url, json=payload, timeout=120)  
    print(f"\nPredict response status: {resp.status_code}") 
    
    if resp.status_code == 200 and resp.content: 
        try:
            result_data = resp.json() 
            print(f"Result type: {type(result_data).__name__}")
            
            if isinstance(result_data, dict):
                for k, v in result_data.items():
                    print(f"  {k}: {str(v)[:200]}") 
            elif isinstance(result_data, list):  
                for i, item in enumerate(result_data[:10]):
                    print(f"  [{i}]: {str(item)[:200]}")  
        except: 
            print(f"Response text (first 500 chars): {resp.text[:500]}") 
    else:
        if resp.content:
            print(f"Error response: {resp.text[:500]}") 
except Exception as e:
    import traceback  
    print(f"Prediction error:\n{traceback.format_exc()}")

print("\nDone.") 
