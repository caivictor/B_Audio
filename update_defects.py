import datetime

with open("DEFECTS.md", "r") as f:
    content = f.read()

import re

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

updates = {
    "DEF-034": "FIX READY - Updated stopCapture() to close WebSockets in WebSocket.CONNECTING state.",
    "DEF-035": "FIX READY - Config updates check if language/task actually changed before clearing buffers.",
    "DEF-036": "FIX READY - Dispatch { action: 'hideCaption' } on stop or captureStopped.",
    "DEF-037": "FIX READY - Wrap both speaker tag and dialogue in colorized <span>.",
    "DEF-038": "FIX READY - Made regex colon optional /\[(Speaker\s*[^\]]+)\]:?/gi.",
    "DEF-039": "FIX READY - Added next_msg.get('type') == 'websocket.disconnect' check to drain loop.",
    "DEF-040": "FIX READY - Made regex colon optional.",
    "DEF-041": "FIX READY - Stored reconnect timer and added clearTimeout in stopCapture.",
    "DEF-042": "FIX READY - Config updates verify state changes before clearing buffer.",
    "DEF-043": "FIX READY - Capped transcriptHistory array to 1000 items.",
    "DEF-044": "FIX READY - Added keepalive ping handling in offscreen.js.",
    "DEF-045": "FIX READY - Clamped fontSize between 12 and 72 in content.js.",
    "DEF-046": "FIX READY - Added await websocket.close() on STT connect failure."
}

for def_id, reason in updates.items():
    content = update_defect(content, def_id, "FIX-READY", reason, f"marked FIX-READY on behalf of developer: {reason}")

with open("DEFECTS.md", "w") as f:
    f.write(content)
