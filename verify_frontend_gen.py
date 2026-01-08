
import os
import shutil
from pathlib import Path
from src.code_generation.enhanced_engine import EnhancedCodeGenerator
from src.config import PipelineConfig

# Mock config
config = PipelineConfig(
    workspace_dir="./test_output",
    frontend={"framework": "nextjs", "styling": "tailwind"}
)

# Mock data
app_name = "TestDash"
description = "A test dashboard app"
entity = {
    "name": "Project",
    "lower": "project",
    "plural": "projects",
    "fields": [
        {"name": "name", "type": "string"},
        {"name": "status", "type": "string"}
    ]
}

# Clean previous output
if os.path.exists("./test_output"):
    shutil.rmtree("./test_output")
os.makedirs("./test_output")

# Instantiate generator
generator = EnhancedCodeGenerator("./test_output")

# Run frontend generation
print("Generating frontend...")
generator._generate_frontend(app_name, description, entity)

# Check results
frontend_dir = Path("./test_output/frontend")
if not frontend_dir.exists():
    print("FAILED: frontend directory not created")
    exit(1)

required_files = [
    "package.json",
    "src/app/globals.css",
    "src/app/layout.tsx",
    "src/app/page.tsx",
    "src/app/(auth)/login/page.tsx",
    "src/app/(auth)/register/page.tsx",
    "src/app/(dashboard)/layout.tsx",
    "src/app/(dashboard)/dashboard/page.tsx",
    "src/components/ui/button.tsx",
    "src/components/ui/card.tsx",
    "src/components/icons.tsx"
]

missing = []
for f in required_files:
    if not (frontend_dir / f).exists():
        missing.append(f)

if missing:
    print(f"FAILED: Missing files: {missing}")
else:
    print("SUCCESS: All frontend files generated!")
    
    # Optional: content check
    with open(frontend_dir / "package.json", "r") as f:
        pkg = f.read()
        if "recharts" not in pkg:
            print("WARNING: recharts dependency missing in package.json")
        else:
            print("Verified: recharts in package.json")

