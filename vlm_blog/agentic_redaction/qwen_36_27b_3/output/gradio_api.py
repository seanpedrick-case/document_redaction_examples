import requests, re, json

base = "https://seanpedrickcase-document-redaction.hf.space" 
r = requests.get(base, timeout=15) 
html = r.text

# Extract config JSON  
start_idx = html.find('config = ')
brace_start = html.index('{', start_idx)
depth, i, in_string, escape_next = 0, brace_start, False, False

while i < len(html):
    c = html[i]
    if escape_next: 
        escape_next = False  
        i += 1
        continue
    if c == '\\': 
        escape_next = True  
        i += 1
        continue
    if c == '"': 
        in_string = not in_string
    
    if not in_string: 
        if c == '{': depth += 1
        elif c == '}': 
            depth -= 1
            if depth == 0: break
    
    i += 1

cfg_str = html[brace_start:i+1]
cfg = json.loads(cfg_str)

# Build component type map  
comp_map = {c['id']: c.get('type') for c in cfg['components']}

def get_id(x):
    if isinstance(x, dict): return x.get('id', x) 
    return x

# Look at dependencies - these map component events to function calls  
deps = cfg.get('dependencies', []) 
print(f"Dependencies count: {len(deps)}") 

for dep in deps[:50]:
    fn_index = dep.get('fn_index') 
    triggers = dep.get('triggers', [])
    inputs_list = dep.get('inputs', [])  
    outputs_list = dep.get('outputs', []) 
    
    trigger_info = "" 
    if triggers: 
        trig_comp_type = comp_map.get(triggers[0], 'unknown')  
        trigger_info = f"trigger={triggers[0]}({trig_comp_type})"
    
    inputs_str = ','.join(str(get_id(x)) for x in inputs_list[:5])
    outputs_str = ','.join(str(get_id(x)) for x in outputs_list[:5])
    
    print(f"\nfn_index={fn_index}: {trigger_info} | in=[{inputs_str}] out=[{outputs_str}]")

# Also look at the api_map which maps API names to function indices  
api_map = cfg.get('api_map', {}) 
print(f"\nAPI map ({len(api_map)} entries):")
for name, info in list(api_map.items())[:20]:
    print(f"  {name}: fn_index={info['fn_index']}, api_name={info.get('api_name')}")

# Get the full API info  
api_info = cfg.get('api_info', {}) 
print(f"\nAPI info keys: {list(api_info.keys())[:10]}")
if 'fns' in api_info:
    print(f"Functions ({len(api_info['fns'])}):")
    for fn in api_info['fns'][:25]:
        print(f"  fn_index={fn.get('fn_index')}, name={fn.get('name')}, type={fn.get('type')}")
