import os

files = [
    "../../web/src/store/useChatStore.ts",
    "../../web/src/app/page.tsx",
    "../../web/src/components/dashboard/ExecutiveDashboard.tsx"
]

out_path = "/Users/cuthbertrwebilumi/Desktop/Maestro/prompts/Sprint_012_Step3_CTO_Review_Package.md"

with open(out_path, "w") as out:
    out.write("# MAESTRO — Sprint 012 Step 3 (Multi-Tenant Hydration) CTO Review Package\n\n")
    out.write("Paste this entire document into ChatGPT for the code review.\n\n")
    out.write("---\n\n")
    out.write("## Context\n\n")
    out.write("Sprint 012 Step 3: Multi-Tenant Hydration.\n")
    out.write("This document contains the updates to the global Zustand store, the page layout to fetch the organization and replace the hardcoded DEFAULT_ORG_ID, and the fetcher updates.\n\n")
    out.write("---\n\n")

    for fpath in files:
        full_path = os.path.abspath(os.path.join("/Users/cuthbertrwebilumi/Desktop/Maestro/backend/maestro", fpath))
        if os.path.exists(full_path):
            ext = full_path.split(".")[-1]
            if ext == "py": lang = "py"
            elif ext in ("tsx", "ts", "js", "jsx"): lang = "tsx"
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
