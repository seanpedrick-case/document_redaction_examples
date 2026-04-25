#!/usr/bin/env python3  
"""Direct HTTP calls to Gradio API - complete pipeline."""

import json, os, time, uuid, re

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

# Step 1: Upload PDF  
print("Step 1: Uploading PDF...")  
upload_url = f"{base}/gradio_api/upload" 

with open(pdf_path, 'rb') as f:
    files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
    resp = session.post(upload_url, files=files)

print(f"Upload status: {resp.status_code}") 
upload_data = resp.json() if resp.content else {}  
if isinstance(upload_data, dict):
    print(f"Upload data keys: {list(upload_data.keys())}")

# Get session ID from cookies 
session_id = None  
for cookie in session.cookies:
    if 'gradio' in cookie.name.lower() or 'session' in cookie.name.lower(): 
        session_id = cookie.value  

if not session_id:
    import uuid as _uuid
    session_id = str(_uuid.uuid4())

print(f"Session ID: {session_id}") 

# Step 2: Get config  
print("\nStep 2: Getting config...") 
config_resp = requests.get(base, timeout=30) 
cfg_text = config_resp.text

start_idx = cfg_text.find('window.config')
cfg_json_str = None
if start_idx > -1:
    brace_count = 0  
    in_brace = False  
    json_start_pos = start_idx + len('window.config')  
    
    for i, ch in enumerate(cfg_text[json_start_pos:], json_start_pos): 
        if ch == '{': 
            brace_count += 1; in_brace = True
        elif ch == '}': 
            brace_count -= 1
            if in_brace and brace_count == 0:  
                cfg_json_str = cfg_text[json_start_pos:i+1]  

if not cfg_json_str:
    print("ERROR: Could not find config JSON")
else:
    try:
        config_data = json.loads(cfg_json_str) 
    except Exception as e:
        print(f"Config parse error: {e}")
