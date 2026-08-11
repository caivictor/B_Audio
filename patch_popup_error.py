with open("extension/popup.js", "r") as f:
    content = f.read()

content = content.replace(
    "statusDiv.textContent = 'Status: Failed to start';",
    "statusDiv.textContent = 'Status: Failed to start (' + (response.error || 'Unknown') + ')';"
)

with open("extension/popup.js", "w") as f:
    f.write(content)
