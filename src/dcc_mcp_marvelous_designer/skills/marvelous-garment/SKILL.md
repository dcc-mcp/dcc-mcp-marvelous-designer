---
name: marvelous-garment
description: Typed Marvelous Designer pattern creation and bounded simulation.
metadata:
  dcc-mcp:
    dcc: marvelous_designer
    version: "0.1.1"
    layer: domain
    tags: [garment, pattern, simulation]
    tools: tools.yaml
---

# marvelous-garment

Use only with the exact native Marvelous Designer instance. Read status first.
Save existing work before replacement or mutation. All host calls require main
thread dispatch. Simulation is synchronous and cannot be interrupted mid-call;
never assume timeout means stopped and never blindly retry a mutation.

Exports require an empty project-root directory. Inspect hashes and validate
source dimensions, materials and motion independently in both Unreal and Unity.
Offline cache playback is not runtime cloth. Missing API/host/license is a blocker,
not permission to fall back to arbitrary scripts or UI input.
