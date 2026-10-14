import os

files = [
    "app/api/v1/router.py",
    "app/modules/business/router.py",
    "app/modules/business/schemas.py"
]

out_path = "/Users/cuthbertrwebilumi/Desktop/Maestro/prompts/Sprint_011_Step1_CTO_Review_Package.md"

with open(out_path, "w") as out:
    out.write("# MAESTRO — Sprint 011 Step 1 CTO Review Package\n\n")
    out.write("Paste this entire document into ChatGPT for the code review.\n\n")
    out.write("---\n\n")
    out.write("## Context\n\n")
    out.write("Sprint 011 Step 1 (Backend Scaffold) is on branch `main`.\n")
    out.write("This document contains the backend implementation files for the Dashboard API.\n\n")
    out.write("---\n\n")

    for fpath in files:
        full_path = os.path.join("/Users/cuthbertrwebilumi/Desktop/Maestro/backend/maestro", fpath)
        if os.path.exists(full_path):
            ext = fpath.split(".")[-1]
            if ext == "py": lang = "py"
            elif ext == "json": lang = "json"
            else: lang = "text"

            out.write(f"## `{fpath}`\n\n")
            out.write(f"```{lang}\n")
            with open(full_path, "r") as f:
                out.write(f.read().strip())
            out.write("\n```\n\n---\n\n")
        else:
            print(f"Warning: {full_path} not found")

print(f"Created {out_path}")
