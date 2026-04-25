#!/usr/bin/env python3  
import fitz  
import re, os

base_dir = "/home/spedrickcase/output" 
output_dir = os.path.join(base_dir, "gradio_output") 
os.makedirs(output_dir, exist_ok=True) 

pdf_path = "/home/spedrickcase/Partnership-Agreement-Toolkit_0_0.pdf"
doc = fitz.open(pdf_path)

email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
phone_pattern = r'\b(?:\+?1[-. \s]?)?\( ?\d{3}\)?[-. \s]?\d{3}[-. \s]?\d{4}\b'
target_terms = ['London', 'Sister City']  

print(f"Processing {len(doc)} pages...") 
redactions = []

for page_idx in range(len(doc)):
    page = doc[page_idx]  
    text = page.get_text() 
    words = page.get_text("words") 
    
    for match in re.finditer(email_pattern, text):
        email = match.group() 
        best_bbox = None 
        for w in words:
            x0,y0,x1,y1=float(w[0]),float(w[1]),float(w[2]),float(w[3])
            if email.lower()==w[4].strip().lower():
                best_bbox=(page_idx+1,x0-2,y0-2,x1+5,y1+2)
                break
        if best_bbox: redactions.append(best_bbox); print(f"  Page {page_idx+1} EMAIL:{email}")

    for match in re.finditer(phone_pattern, text):
        phone=match.group(); clean_phone=phone.replace(' ','').replace('-','') 
        best_bbox=None
        for w in words:
            x0,y0,x1,y1=float(w[0]),float(w[1]),float(w[2]),float(w[3])
            if clean_phone==re.sub(r'[\s\-]','',w[4].strip()):
                best_bbox=(page_idx+1,x0-2,y0-2,x1+5,y1+2)
                break
        if best_bbox: redactions.append(best_bbox); print(f"  Page {page_idx+1} PHONE:{phone}")

    for term in target_terms:
        pattern=re.compile(re.escape(term),re.IGNORECASE) 
        for match in pattern.finditer(text):
            term_found=match.group() 
            best_bbox=None; running_text="" 
            
