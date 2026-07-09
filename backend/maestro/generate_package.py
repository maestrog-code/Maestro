import os

files = [
    "app/ai/pipeline/executor.py",
    "app/ai/agents/registry.py",
    "app/core/ai_settings.py",
    "app/ai/agents/definitions/ceo.py",
    "app/ai/prompts/templates/ceo_system.md",
    "app/ai/tools/orchestration_tools.py",
    "app/modules/ai_conversations/models.py",
    "alembic/versions/007_add_parent_message_id.py"
]

out_path = "/Users/cuthbertrwebilumi/Desktop/Maestro/prompts/Sprint_007_CTO_Review_Package.md"

with open(out_path, "w") as out:
    out.write("# MAESTRO — Sprint 007 CTO Review Package\n\n")
    out.write("Paste this entire document into ChatGPT for the code review.\n\n")
    out.write("---\n\n")
    out.write("## Context\n\n")
    out.write("Sprint 007 is on branch `feature/agent-orchestration-engine`.\n")
    out.write("This document contains every implementation file in full, exactly as committed.\n\n")
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
