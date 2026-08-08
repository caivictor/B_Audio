import re

with open("DEFECTS.md", "r") as f:
    content = f.read()

def update_defect(content, def_id, new_status, reason, history_line):
    # Find the block for the defect
    pattern = rf"(## {def_id}:.*?)- Status: OPEN(.*?)History:(.*?)(?=## DEF-|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"Could not find {def_id} in OPEN status.")
        return content
    
    header = match.group(1)
    middle = match.group(2)
    history = match.group(3).rstrip()
    
    # Replace the block
    new_block = f"{header}- Status: {new_status}{middle}History:{history}\n- orchestrator: {history_line}\n\n"
    
    content = content[:match.start()] + new_block + content[match.end():]
    return content

content = update_defect(content, "DEF-011", "FIX-READY", "FIX READY — Updated `TransparentOverlayWindow._update_geometry()` in `client/main.py` to calculate the required wrapped label height using `self.label.heightForWidth(label_width)` and enforce it with `self.setFixedHeight(req_height)` using `not self.label.isHidden()` visibility checks.", "marked FIX-READY on behalf of frontend-dev: FIX READY — Updated `TransparentOverlayWindow._update_geometry()` in `client/main.py` to calculate the required wrapped label height using `self.label.heightForWidth(label_width)` and enforce it with `self.setFixedHeight(req_height)` using `not self.label.isHidden()` visibility checks.")

with open("DEFECTS.md", "w") as f:
    f.write(content)
