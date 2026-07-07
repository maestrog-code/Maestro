import os

files = [
    "app/modules/knowledge/models.py",
    "app/modules/knowledge/schemas.py",
    "app/modules/knowledge/repositories.py",
    "app/modules/knowledge/services.py",
    "app/modules/knowledge/router.py",
    "app/modules/knowledge/parsers.py",
    "app/ai/tools/knowledge_tools.py",
    "app/ai/vector_store/pgvector.py",
    "app/modules/knowledge/chunking.py",
    "app/ai/pipeline/executor.py",
    "app/ai/prompts/builder.py",
    "app/ai/agents/definitions/ceo.py",
    "app/ai/agents/definitions/cfo.py",
    "alembic/versions/003_knowledge_engine.py",
    "app/api/v1/router.py",
    "app/workers/knowledge_tasks.py",
    "tests/api/test_knowledge_e2e.py",
    "tests/retrieval/golden_queries.json",
    "tests/retrieval/benchmark.py",
    "app/ai/embedding/base.py",
    "app/ai/embedding/google.py",
    "app/ai/storage/base.py",
    "app/ai/storage/local.py"
]

out_path = "/Users/cuthbertrwebilumi/Desktop/Maestro/prompts/Sprint_005_CTO_Review_Package.md"

with open(out_path, "w") as out:
    out.write("# MAESTRO — Sprint 005 CTO Review Package\n\n")
    out.write("Paste this entire document into ChatGPT for the code review.\n\n")
    out.write("---\n\n")
    out.write("## Context\n\n")
    out.write("Sprint 005 is on branch `feature/organizational-knowledge-engine`.\n")
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
