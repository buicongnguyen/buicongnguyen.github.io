# Lab 06 — URDF-to-USD Robot Model Audit

- **Prerequisite:** Labs 01–05 pass and the evidence package identifies the simulator/workspace version.
- **Goal:** prove that a robot description is structurally valid before tuning its simulated behavior.
- **Pass:** the offline URDF gate passes, imported USD ownership is understood, colliders/inertias/joints are inspected, and a repeatable dynamic smoke test has no unexplained instability.

- Live page: <https://buicongnguyen.github.io/robotics-simulation-engineer/lab-06-urdf-model-audit.html>
- [NVIDIA URDF Import tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/importer_exporter/import_urdf.html)
- [NVIDIA URDF Importer reference](https://docs.isaacsim.omniverse.nvidia.com/latest/importer_exporter/ext_isaacsim_asset_importer_urdf.html)
- [NVIDIA Physics Inspector](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/physics/physics_inspector.html)
- Auditor: [lab-assets/urdf_audit.py](lab-assets/urdf_audit.py)

## Why model audit precedes tuning

```mermaid
flowchart LR
    Source["URDF source<br/>links + joints + inertials"] --> Audit["Offline invariants"]
    Audit --> Import["Importer choices"]
    Import --> USD["USD articulation + colliders"]
    USD --> Smoke["Dynamic smoke test"]
    Smoke --> Evidence["Model audit report"]
```

Friction cannot repair a disconnected tree. Damping cannot repair a wrong joint axis. More solver iterations cannot repair a non-physical inertia matrix. Fix the earliest invalid contract.

## Definitions that must stay separate

| Term | Meaning | Typical failure |
|---|---|---|
| Visual geometry | what the renderer draws | pretty model hides bad physics |
| Collision geometry | shapes used for contact | mesh too complex, missing, intersecting, or oversized |
| Inertial frame | center of mass and inertia orientation | unexpected tipping or oscillation |
| Joint frame/axis | permitted relative motion | sign, axis, or origin error |
| Articulation root | solver ownership boundary | wrong root or disconnected links |
| Drive | control law applied at a joint | position/velocity/effort mismatch |

## Step 1 — run the offline gate

Use the supplied known-good fixture first:

```powershell
$Root = "C:\Users\n\source\repos\issac_sim\robotics-simulation-engineer"
C:\isaacsim-6.0.1\python.bat "$Root\lab-assets\urdf_audit.py" `
  "$Root\lab-assets\fixtures\valid_robot.urdf" `
  --output "$Root\lab-assets\fixtures\valid_robot_report.json"
```

The auditor checks:

- exactly one root link and a connected acyclic link graph;
- one parent joint per child;
- valid parent/child references and unique names;
- finite positive mass and a positive-definite inertia matrix;
- required limits for revolute/prismatic joints;
- positive effort/velocity limits;
- declared collision and inertial blocks.

Warnings are review items, not automatic proof of failure. For example, a deliberately massless frame may be fixed into a parent, but that decision must be recorded.

## Step 2 — perform a planted-fault test

Copy the fixture and change one invariant at a time:

1. Set a mass to zero.
2. Make a joint child reference an unknown link.
3. Make `ixx` negative.
4. Remove one collision block.

The first three must fail; the missing collider is reported for review. Restore the original before continuing. A validator that never fails is not evidence.

## Step 3 — record import choices before clicking Import

In Isaac Sim choose **File → Import**, select the URDF, and write an import manifest:

| Setting | Decision to record | Why it matters |
|---|---|---|
| USD output | project-owned path | avoids editing generated cache content |
| Fix base | true only for anchored robots | changes degrees of freedom |
| Self collision | justified on/off | affects contact count and stability |
| Collider type | simple/convex decomposition | accuracy/performance tradeoff |
| Drive type | force or acceleration | changes mass sensitivity |
| Joint target | none/position/velocity | must match controller semantics |
| Default density | fallback only | must not silently replace known masses |

Do not overwrite the source URDF. Treat imported USD as a generated layer and place project-specific overrides in a separate USD layer when practical.

## Step 4 — inspect the imported USD

In the Stage and Property panels verify:

1. The intended prim owns `ArticulationRootAPI`.
2. Each physical link has the expected rigid body and collider.
3. Collision shapes match the visual silhouette without unnecessary detail.
4. Joint axes and limits agree with the source model.
5. Wheel joints use velocity drives; torque-controlled joints do not inherit position drives.
6. Mass and center of mass are plausible in SI units.
7. No colliders begin interpenetrating at the nominal pose.

Turn on viewport collision visualization: **eye icon → Show by type → Physics → Colliders → All**. Use Physics Inspector for joint limits, drives, and articulation behavior.

## Step 5 — run a deterministic smoke sequence

```mermaid
stateDiagram-v2
    [*] --> Loaded
    Loaded --> Settling: Play with zero command
    Settling --> Stable: pose finite and bounded
    Settling --> Failed: explosion, drift, penetration
    Stable --> Exercising: command one joint
    Exercising --> Reset: stop and reopen stage
    Reset --> Settling: repeat same seed/config
```

Run at least three identical trials:

- 5 seconds at zero command;
- one low-amplitude joint or wheel command;
- explicit zero command;
- Stop, reopen the saved stage, and repeat.

Record initial/final pose, maximum joint speed, warnings, visible penetrations, and whether reset reproduces the result.

## Debugging decision tree

```mermaid
flowchart TD
    A["Unstable model"] --> B{"Offline graph/inertia gate passes?"}
    B -->|No| C["Fix URDF source"]
    B -->|Yes| D{"Colliders overlap or are too complex?"}
    D -->|Yes| E["Simplify/reposition collision geometry"]
    D -->|No| F{"Joint axis, limit, drive correct?"}
    F -->|No| G["Fix model/control semantics"]
    F -->|Yes| H["Then inspect timestep and solver settings"]
```

## Evidence and gate

Save the source hash, auditor JSON, import manifest, Stage screenshot with API ownership, collider screenshot, inertia/joint table, three smoke-test rows, and one planted-fault result.

**Gate:** proceed only when structure and physical metadata are explainable, the imported articulation behaves repeatably, and no tuning parameter is being used to conceal a model defect.

Next: [Lab 07 — Physics identification](lab-07-physics-identification.md).
