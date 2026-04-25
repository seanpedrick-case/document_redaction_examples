#!/usr/bin/env python3  
"""Redact PII from PDF using PyMuPDF - no external OCR needed."""

import fitz  # PyMuPDF 
import re, os, json

base_dir = "/home/spedrickcase/output" 
output_dir = os.path.join(base_dir, "gradio_output")
os.makedirs(output_dir, exist_ok=True) 

pdf_path = "/home/spedrickcase/Partnership-Agreement-Toolkit_0_0.pdf"
doc = fitz.open(pdf_path)

# PII detection patterns  
pii_patterns = { 
    'EMAIL_ADDRESS': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'PHONE_NUMBER': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', 
    'PERSON': None,  # Will use word-based detection  
    'STREETNAME': None,
    'UKPOSTCODE': None,
}

# Also detect specific terms the user wants redacted  
target_terms = ['London', 'Sister City']  

print(f"Processing {len(doc)} pages...") 

# Store all redaction boxes: [(page_num, x0, y0, x1, y1), ...] 
redactions = []

for page_idx in range(len(doc)):
    page = doc[page_idx]
    text = page.get_text() 
    
    print(f"\nPage {page_idx+1}:")  
    print(f"  Text length: {len(text)} chars") 
    
    # Get word blocks for position info  
    words = page.get_text("words")  # List of (x0, y0, x1, y1, word) tuples
    
    # Detect emails 
    for match in re.finditer(pii_patterns['EMAIL_ADDRESS'], text):
        email = match.group() 
        start_pos = match.start()
        
        # Find position in words list  
        for w_idx, (x0, y0, x1, y1, word) in enumerate(words):
            if email.lower() in word.lower(): 
                redactions.append((page_idx+1, x0*72/72.0-72*page.mediabox[0], y0*72/72.0-72*page.mediabox[3], x1*72/72.0-72*page.mediabox[0]+5, y1))
                print(f"  EMAIL: {email} at ({x0:.1f}, {y0:.1f})")  
                break
    
    # Detect phone numbers 
    for match in re.finditer(pii_patterns['PHONE_NUMBER'], text):
        phone = match.group() 
        start_pos = match.start() 
        
        # Find position in words list  
        found = False 
        for w_idx, (x0, y0, x1, y1, word) in enumerate(words):
            if phone.replace(' ', '').replace('-', '') == word.replace(' ', '').replace('-', ''):
                redactions.append((page_idx+1, x0-72*page.mediabox[0], y0-72*page.mediabox[3], x1-72*page.mediabox[0]+5, y1)) 
                print(f"  PHONE: {phone} at ({x0:.1f}, {y0:.1f})")
                found = True  
                break
        if not found: 
            # Try partial match  
            for w_idx, (x0, y0, x1, y1, word) in enumerate(words):
                if phone[:5] in word or phone[-4:] in word: 
                    redactions.append((page_idx+1, x0-72*page.mediabox[0], y0-72*page.mediabox[3], x1-72*page.mediabox[0]+5, y1))
                    print(f"  PHONE (partial): {phone} at ({x0:.1f}, {y0:.1f})") 
                    break
    
    # Detect target terms (London, Sister City)  
    for term in target_terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE) 
        for match in pattern.finditer(text):
            term_found = match.group() 
            start_pos = match.start() 
            
            # Find position in words list  
            found_word_start = None  
            found_word_end = None
            
            # Build a running string from words and find where this term appears
            running_text = "" 
            