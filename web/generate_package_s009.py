import os

files = [
    "package.json",
    "postcss.config.mjs",
    "src/app/globals.css",
    "src/store/useChatStore.ts",
    "src/lib/api/chat.ts",
    "src/components/chat/AgentStatus.tsx",
    "src/app/page.tsx"
]

out_path = "/Users/cuthbertrwebilumi/Desktop/Maestro/prompts/Sprint_009_CTO_Review_Package.md"

with open(out_path, "w") as out:
    out.write("# MAESTRO — Sprint 009 CTO Review Package\n\n")
    out.write("Paste this entire document into ChatGPT for the code review.\n\n")
    out.write("---\n\n")
    out.write("## Context\n\n")
    out.write("Sprint 009 is on branch `feature/sprint-009-frontend-ui`.\n")
    out.write("This document contains every implementation file in full, exactly as committed.\n\n")
    out.write("---\n\n")

    for fpath in files:
        full_path = os.path.join("/Users/cuthbertrwebilumi/Desktop/Maestro/web", fpath)
        if os.path.exists(full_path):
            ext = fpath.split(".")[-1]
            if ext == "py": lang = "py"
            elif ext == "ts": lang = "typescript"
            elif ext == "tsx": lang = "tsx"
            elif ext == "css": lang = "css"
            elif ext == "mjs" or ext == "js": lang = "javascript"
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
