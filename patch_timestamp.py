with open("extension/content.js", "r") as f:
    content = f.read()

# Update content.js to accept start/end if we want, but actually it just uses text.
# The issue is we need to ensure the extension still renders properly.
pass
