#!/usr/bin/env python3  
"""Use gradio_client to run document redaction on HF Space."""

import sys, os, json

sys.path.insert(0, '/home/spedrickcase/.local/lib/python3.12/site-packages')

from gradio_client import Client, file as gr_file
from gradio_client import utils as gc_utils

SPACE_URL = "https://seanpedrickcase-document-redaction.hf.space" 
PDF_PATH = "/home/spedrickcase/Partnership-Agreement-Toolkit_0_0.pdf"
OUTPUT_DIR = "/home/spedrickcase/output/gradio_output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Connecting to {SPACE_URL}...")  
try:
    client = Client(SPACE_URL, download_files=OUTPUT_DIR, verbose=False) 
except Exception as e:
    print(f"Connection error (will retry with ssl_verify): {e}")
    client = Client(SPACE_URL, download_files=OUTPUT_DIR, verbose=False, httpx_kwargs={'verify': False})

# Get app info  
try:
    info = client.view_info() 
except Exception as e:
    print(f"view_info error (may be Gradio v6): {e}")
    # Try alternate approach for Gradio v6  
    try:
        info = client.api('/info') if hasattr(client, 'api') else {}
    except Exception as e2: 
        print(f"Alternate info error: {e2}")  
        info = {}

print(f"\nApp version: {info.get('version', 'unknown')}") 
print(f"Mode: {info.get('mode', 'unknown')}") 

# List functions  
fns = info.get('api_info', {}).get('fns', [])
print(f"\nFunctions ({len(fns)}):")
for fn in fns[:30]:
    print(f"  fn_index={fn['fn_index']}, name={fn['name']}")

# List components  
comps = info.get('components', []) 
print(f"\nComponents ({len(comps)}):")

file_ids = [] 
btn_map = {}
for comp in comps:
    ctype = comp.get('type')
    if ctype == 'file':
        file_ids.append(comp['id'])  
        print(f"  FILE: id={comp['id']}") 
    elif ctype == 'button':  
        val = str(comp.get('value', ''))[:60]
        btn_map[val] = comp['id']

print(f"\nFile upload component IDs: {file_ids}")
print(f"Buttons with 'Extract' or 'Review' in name:") 
for text, bid in btn_map.items():  
    if any(k in text for k in ['Extract', 'Review', 'Redact']):
        print(f"  '{text}' -> fn_index={bid}")

# Try to find the predict function by looking at dependencies
deps = info.get('dependencies', [])
print(f"\nDependencies ({len(deps)}):") 
for dep in deps[:15]:  
    fn_idx = dep.get('fn_index') or 'N/A'
    triggers = dep.get('triggers', [])
    inputs_list = dep.get('inputs', [])
    outputs_list = dep.get('outputs', []) 
    
    # Get component types for reference 
    comp_type_map = {c['id']: c.get('type') for c in comps}
    
    trigger_text = ""  
    if triggers: 
        trig_id = triggers[0] if isinstance(triggers[0], int) else (triggers[0].get('id', '?') if isinstance(triggers[0], dict) else str(triggers[0]))[:5]
        trig_type = comp_type_map.get(trig_id, 'unknown')
        trigger_text = f"trigger={trig_id}({trig_type})" 
    
    inputs_str = ",".join(str(x.get('id', x) if isinstance(x, dict) else x)[:5] for x in (inputs_list[:3])) 
    outputs_str = ",".join(str(x.get('id', x) if isinstance(x, dict) else x)[:5] for x in (outputs_list[:3])) 
    
    print(f"  fn={fn_idx}: {trigger_text} | in=[{inputs_str}] out=[{outputs_str}]")

print("\n\n=== Now attempting redaction ===")
print("This will upload the PDF and run OCR + PII detection...")
print("Press Ctrl+C to cancel.\n")

# Try to find which function does the actual redaction 
# It should take a file input as one of its inputs  
redact_fn = None 
for dep in deps:
    fn_idx = dep.get('fn_index') or 'N/A'
    inputs_list = dep.get('inputs', []) 
    
    # Check if any input is a file component
    for inp in inputs_list: 
        inp_id = inp['id'] if isinstance(inp, dict) else inp  
        if comp_type_map.get(inp_id) == 'file':
            print(f"\nFound redaction function: fn_index={fn_idx}")
            print(f"  Inputs: {[x.get('id', x) for x in inputs_list[:5]]}") 
            print(f"  Outputs: {[x.get('id', x) for x in dep.get('outputs', [])[:5]]}")
            redact_fn = fn_idx  
            break
    
    if redact_fn is not None and isinstance(redact_fn, (int, str)):
        break

if redact_fn is None:
    print("\nCould not identify the main redaction function from dependencies.") 
    print("Will try calling predict with file path directly...") 

# Try to run the prediction  
print(f"\nAttempting predict call with fn_index={redact_fn}...")
