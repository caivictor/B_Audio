import json

with open("extension/manifest.json", "r") as f:
    manifest = json.load(f)

manifest["version"] = "1.0.0"

with open("extension/manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)
