#!/usr/bin/env python3  
"""Build fully redacted PDF from review CSV rules."""

import fitz, csv, os, json

out_dir = "/home/spedrickcase/output/gradio_output" 
os.makedirs(out_dir, exist_ok=True) 

pdf_path = "/home/spedrickcase/Partnership-Agreement-Toolkit_0_0.pdf...[truncated]