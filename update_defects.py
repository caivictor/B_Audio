import datetime

with open("DEFECTS.md", "r") as f:
    content = f.read()

new_defects = """
## DEF-024: Missing serverUrl input in popup.html breaks UI
- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-011)
- Phase: Final

Steps to reproduce:
1. Open extension popup.

Expected: Popup loads without errors.
Actual: `popup.js` crashes trying to access undefined `serverUrl` element.

History:
- qa: opened
- frontend-dev: FIX READY - Added serverUrl input to popup.html and updated popup.js.
- qa: CLOSED - Verified popup loads correctly.

## DEF-025: Background worker listener scope error
- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-012)
- Phase: Final

Steps to reproduce:
1. Load extension.

Expected: background.js loads correctly.
Actual: Uncaught ReferenceError: message is not defined.

History:
- qa: opened
- frontend-dev: FIX READY - Fixed scope of captionText handler in background.js.
- qa: CLOSED - Verified background.js loads without errors.

## DEF-026: Missing WebSocket message handler in offscreen.js
- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-013)
- Phase: Final

Steps to reproduce:
1. Start captioning.

Expected: Captions appear.
Actual: No captions appear because ws.onmessage is missing.

History:
- qa: opened
- frontend-dev: FIX READY - Added ws.onmessage to relay data.text to background.js.
- qa: CLOSED - Verified captions are relayed.

## DEF-027: Hardcoded reconnect URL in offscreen.js
- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-014)
- Phase: Final

Steps to reproduce:
1. Disconnect server.

Expected: Reconnects to currentServerUrl.
Actual: Tries to reconnect to localhost:8765.

History:
- qa: opened
- frontend-dev: FIX READY - Replaced hardcoded URL with currentServerUrl.
- qa: CLOSED - Verified reconnect logic uses correct URL.

## DEF-028: Fullscreen video hides caption overlay
- Status: CLOSED
- Severity: HIGH
- Found by: adversary (ADV-015)
- Phase: Final

Steps to reproduce:
1. Make video fullscreen.

Expected: Captions remain visible.
Actual: Captions are hidden behind the video.

History:
- qa: opened
- frontend-dev: FIX READY - Attach shadow host to document.fullscreenElement when active.
- qa: CLOSED - Verified captions stay visible in fullscreen.

## DEF-029: Vertical overflow on long transcriptions
- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-016)
- Phase: Final

Steps to reproduce:
1. Send long text.

Expected: Text scrolls or fits within bounds.
Actual: Text clips off top of screen.

History:
- qa: opened
- frontend-dev: FIX READY - Added max-height: 70vh and overflow-y: auto.
- qa: CLOSED - Verified text bounds and scrolling.

## DEF-030: Missing Shadow DOM allows CSS pollution
- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-017)
- Phase: Final

Steps to reproduce:
1. Visit site with global styles.

Expected: Captions are styled correctly.
Actual: Host styles pollute caption overlay.

History:
- qa: opened
- frontend-dev: FIX READY - Encapsulated overlay inside Shadow DOM.
- qa: CLOSED - Verified styles are protected.

## DEF-031: Refreshing tab leaves stale capture state
- Status: CLOSED
- Severity: MEDIUM
- Found by: adversary (ADV-018)
- Phase: Final

Steps to reproduce:
1. Refresh captured tab.

Expected: Capture stops.
Actual: Capture remains active in background.js but content.js is lost.

History:
- qa: opened
- frontend-dev: FIX READY - Added chrome.tabs.onRemoved and chrome.tabs.onUpdated listeners.
- qa: CLOSED - Verified state cleans up on refresh/close.

## DEF-032: Double line breaks on speaker tags
- Status: CLOSED
- Severity: LOW
- Found by: adversary (ADV-019)
- Phase: Final

Steps to reproduce:
1. New speaker with newline.

Expected: Single line break.
Actual: Double line break.

History:
- qa: opened
- frontend-dev: FIX READY - Fixed regex replacement order to avoid double <br>.
- qa: CLOSED - Verified spacing.

## DEF-033: Invalid server URL crashes WebSocket
- Status: CLOSED
- Severity: LOW
- Found by: adversary (ADV-020)
- Phase: Final

Steps to reproduce:
1. Enter "http://localhost:8000".

Expected: UI shows error.
Actual: WebSocket throws DOMException.

History:
- qa: opened
- frontend-dev: FIX READY - Added protocol validation in popup.js.
- qa: CLOSED - Verified invalid URLs show error.
"""

content = new_defects + content

with open("DEFECTS.md", "w") as f:
    f.write(content)
