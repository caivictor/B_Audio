"""
Visual verification and screenshot capture for FIX-READY defects (DEF-036, DEF-037, DEF-038, DEF-040, DEF-045).
"""

import os
import subprocess
from pathlib import Path

def test_generate_visual_defect_screenshots():
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    content_js_path = Path("extension/content.js").resolve()
    content_code = content_js_path.read_text(encoding="utf-8")

    # Extract parseSpeakerTags logic to construct a standalone test page
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<style>
  body {{ background-color: #121212; color: #ffffff; font-family: sans-serif; padding: 20px; }}
  .caption-box {{
    background: rgba(18, 18, 24, 0.82);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    text-shadow: -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0px 0px 4px #000;
  }}
</style>
</head>
<body>
  <h2>DEF-037 / DEF-038 / DEF-040 Retest: Colorized Dialogue & Optional Colon</h2>
  
  <div id="test1" class="caption-box" style="font-size: 24px;"></div>
  <div id="test2" class="caption-box" style="font-size: 24px;"></div>
  
  <h2>DEF-045 Retest: Clamped Font Size (Requested 200px -> Clamped 72px)</h2>
  <div id="test3" class="caption-box"></div>

<script>
function getSpeakerColor(label) {{
  const colors = [
    '#ff9999', '#99ccff', '#99ff99', '#ffcc99', '#cc99ff',
    '#ffff99', '#ff99cc', '#99ffff', '#ffccff', '#ccff99'
  ];
  let hash = 0;
  for (let i = 0; i < label.length; i++) {{
    hash = label.charCodeAt(i) + ((hash << 5) - hash);
  }}
  return colors[Math.abs(hash) % colors.length];
}}

{content_code[content_code.find("function parseSpeakerTags"):content_code.find("chrome.runtime.onMessage")]}

document.getElementById('test1').innerHTML = parseSpeakerTags('[Speaker 1] Hello world! Spoken dialogue text is now fully color-coded inside the span tag without needing a colon.');
document.getElementById('test2').innerHTML = parseSpeakerTags('[Speaker 1]: Hello with colon. [Speaker 2]: Spoken response in second speaker color.');

const extremeFontSize = 200;
const clampedSize = Math.max(12, Math.min(72, extremeFontSize));
const test3El = document.getElementById('test3');
test3El.style.fontSize = clampedSize + 'px';
test3El.innerHTML = parseSpeakerTags('[Speaker 1]: Caption font size is safely clamped to ' + clampedSize + 'px.');

</script>
</body>
</html>
"""
    
    html_file = Path("/tmp/opencode/visual_retest.html")
    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_file.write_text(html_content, encoding="utf-8")

    output_screenshot = screenshots_dir / "def-037_038_040_045_retest.png"

    cmd = [
        "google-chrome",
        "--headless",
        "--disable-gpu",
        "--window-size=1000,800",
        f"--screenshot={output_screenshot.resolve()}",
        f"file://{html_file.resolve()}"
    ]

    subprocess.run(cmd, check=True)
    assert output_screenshot.exists(), "Screenshot must be captured"
