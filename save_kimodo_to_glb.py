import os
import sys
from pathlib import Path

# Let's save kimodo_to_glb.py locally in scripts/
with open(r"C:\Users\MSI\.gemini\antigravity-ide\brain\d25a63be-8bb9-4834-be7f-a914d52d1bc1\.system_generated\steps\796\content.md", "r", encoding="utf-8") as f:
    text = f.read()

# Extract code from content.md
lines = text.splitlines()[8:] # skip metadata header
code = "\n".join(lines)

with open(r"E:\Kimodo-CPP\scripts\kimodo_to_glb.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Saved E:\\Kimodo-CPP\\scripts\\kimodo_to_glb.py")
