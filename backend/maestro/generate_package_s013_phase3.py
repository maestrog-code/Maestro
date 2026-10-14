import os

files = [
    "../../backend/maestro/render.yaml",
]

out_path = "/Users/cuthbertrwebilumi/Desktop/Maestro/prompts/Sprint_013_Phase3_CTO_Review_Package.md"

with open(out_path, "w") as out:
    out.write("# MAESTRO — Sprint 013 Phase 3 (Infrastructure as Code) CTO Review Package\n\n")
    out.write("Paste this entire document into ChatGPT for the code review.\n\n")
    out.write("---\n\n")
    out.write("## Context\n\n")
    out.write("Sprint 013 Phase 3: Infrastructure as Code (render.yaml).\n")
    out.write("This document contains the Render Blueprint for spinning up the FastAPI Web Service and Celery Worker synchronously.\n\n")
    out.write("---\n\n")

    for fpath in files:
        full_path = os.path.abspath(os.path.join("/Users/cuthbertrwebilumi/Desktop/Maestro/backend/maestro", fpath))
        if os.path.exists(full_path):
            ext = full_path.split(".")[-1]
            if ext == "py": lang = "py"
            elif ext in ("tsx", "ts", "js", "jsx"): lang = "tsx"
            elif ext == "json": lang = "json"
            elif ext in ("yaml", "yml"): lang = "yaml"
            else: lang = "text"

            out.write(f"## `{fpath}`\n\n")
            out.write(f"```{lang}\n")
            with open(full_path, "r") as f:
                out.write(f.read().strip())
            out.write("\n```\n\n---\n\n")
        else:
            print(f"Warning: {full_path} not found")

print(f"Created {out_path}")
