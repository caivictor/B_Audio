import re

with open("DEFECTS.md", "r") as f:
    content = f.read()

def update_defect(content, def_id, new_status, reason, history_line):
    # Find the block for the defect
    pattern = rf"(## {def_id}:.*?)- Status: OPEN(.*?)History:(.*?)(?=## DEF-|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return content
    
    header = match.group(1)
    middle = match.group(2)
    history = match.group(3).rstrip()
    
    # Replace the block
    new_block = f"{header}- Status: {new_status}{middle}History:{history}\n- orchestrator: {history_line}\n\n"
    
    content = content[:match.start()] + new_block + content[match.end():]
    return content

content = update_defect(content, "DEF-001", "FIX-READY", "FIX READY — Added `@pytest.mark.asyncio` decorator to `test_stt_websocket()` in `server/test_client.py` and handled offline STT server connections.", "marked FIX-READY on behalf of backend-dev: FIX READY — Added `@pytest.mark.asyncio` decorator to `test_stt_websocket()` in `server/test_client.py` and handled offline STT server connections.")

content = update_defect(content, "DEF-002", "FIX-READY", "FIX READY — Updated `run_mock_stt_server` in `client/main.py` to parse JSON config messages dynamically inside the websocket message loop and update language configuration mid-session without returning audio response frames for config messages.", "marked FIX-READY on behalf of frontend-dev: FIX READY — Updated `run_mock_stt_server` in `client/main.py` to parse JSON config messages dynamically inside the websocket message loop and update language configuration mid-session without returning audio response frames for config messages.")

with open("DEFECTS.md", "w") as f:
    f.write(content)
