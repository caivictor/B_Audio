with open("README.md", "r") as f:
    content = f.read()

future_link = """
* [FUTURE_ENHANCEMENTS.md](FUTURE_ENHANCEMENTS.md): Proposed features and architectural improvements for future development cycles.
"""

if "FUTURE_ENHANCEMENTS.md" not in content:
    content = content.replace("## 6. Documentation & Handover Requirements", "## 6. Documentation & Handover Requirements\n" + future_link)
    with open("README.md", "w") as f:
        f.write(content)
