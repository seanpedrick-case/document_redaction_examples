#!/usr/bin/env python3  
"""Direct HTTP calls to Gradio API - no gradio_client dependency."""

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
    for k, v in upload_data.items():
        print(f"  {k}: {str(v)[:200]}")

# Get session ID from cookies 
session_id = None  
for cookie in session.cookies:
    if 'gradio' in cookie.name.lower() or 'session' in cookie.name.lower(): 
        session_id = cookie.value  

if not session_id:
    import uuid 
    session_id = str(uuid.uuid4())

print(f"Session ID: {session_id}") 

# Step 2: Get config  
print("\nStep 2: Getting config...") 
config_resp = requests.get(base, timeout=30) 
cfg_text = config_resp.text

import re
start_idx = cfg_text.find('window.config')
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
                json_end = i + 1  
                cfg_json_str = cfg_text[json_start_pos:json_end]  
               try: 
                    config_data = json.loads(cfg_json_str) 
                    comps = config_data.get('components', [])  
                    comp_types_map = {c['id']: c.get('type') for c in comps}

                    # Find prepare_image_or_pdf_with_efficient_ocr dependency (fn_index=15)  
                    deps = config_data.get('dependencies', []) 
                    dep15 = deps[15] if len(deps) > 15 else None
                    
                    if dep15:
                        inputs_list = dep15.get('inputs', [])
                        print(f"\nDependency fn_index=15 ({len(inputs_list)} inputs):")  
                        
                        # Build args matching gradio_client's internal handling  
                        args = [] 
                        for inp in inputs_list:
                            cid = inp['id'] if isinstance(inp, dict) else inp  
                            ctype = comp_types_map.get(cid, 'unknown') 
                            
                            if ctype == 'file': 
                                uploaded_ref = None
                                if isinstance(upload_data, dict):
                                    ul_files = upload_data.get('files', [])
                                    if isinstance(ul_files, list) and len(ul_files) > 0:  
                                        uploaded_ref = ul_files[0] 
                                
                                if uploaded_ref and isinstance(uploaded_ref, str): 
                                    args.append({'path': uploaded_ref, 'meta': {'_type': 'gradio.FileData'}})
                                else:
                                    args.append([{'path': pdf_path, 'meta': {'_type': 'gradio.FileData'}}])
                                    
                            elif ctype == 'radio' and cid == 19:  
                                args.append('Local OCR model - PDFs without selectable text') 
                            elif ctype in ('checkbox',):
                                args.append(False) 
                            elif ctype == 'textbox':
                                # Check if textbox has a value from component definition  
                                comp_def = next((c for c in comps if c['id'] == cid), {})  
                                val = comp_def.get('value', '') 
                                args.append(str(val).strip() if val else None) 
                            elif ctype == 'number':
                                comp_def = next((c for c in comps if c['id'] == cid), {})  
                                args.append(comp_def.get('value', 0)) 
                            elif ctype == 'dropdown':
                                comp_def = next((c for c in comps if c['id'] == cid), {})  
                                choices = comp_def.get('choices', [])  
                                first_choice = choices[0][0] if isinstance(choices, list) and len(choices) > 0 else '' 
                                args.append(first_choice) 
                            elif ctype == 'state':
                                comp_def = next((c for c in comps if c['id'] == cid), {})  
                                sv = comp_def.get('value', None) 
                                # Keep state as-is (None is valid for states)
                                args.append(sv) 
                            elif ctype == 'button': pass 
                            else:
                                args.append('')
                        
                        print(f"Built {len(args)} arguments")  
                        print(f"Arg types: {[type(a).__name__ for a in args]}")
