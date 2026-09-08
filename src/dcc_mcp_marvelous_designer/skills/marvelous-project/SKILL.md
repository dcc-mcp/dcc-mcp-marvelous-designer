---
name: marvelous-project
description: Typed Marvelous Designer project inspection and interchange.
metadata:
  dcc-mcp:
    dcc: marvelous_designer
    tools: tools.yaml
---

# marvelous-project

Use only with the exact native Marvelous Designer instance. Read status first.
Save existing work before replacement or mutation. All host calls require main
thread dispatch. Simulation is synchronous and cannot be interrupted mid-call;
never assume timeout means stopped and never blindly retry a mutation.

Exports require an empty project-root directory. Inspect hashes and validate
source dimensions, materials and motion independently in both Unreal and Unity.
Offline cache playback is not runtime cloth. Missing API/host/license is a blocker,
not permission to fall back to arbitrary scripts or UI input.
