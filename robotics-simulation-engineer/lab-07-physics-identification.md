# Lab 07 — Physics Parameter Identification

- **Prerequisite:** Lab 06 model audit passes.
- **Goal:** estimate a defensible nominal parameter set from controlled simulation response data.
- **Pass:** repeatability is measured, one parameter family is swept at a time, a declared score selects a candidate, and the candidate improves held-out behavior.

- Live page: <https://buicongnguyen.github.io/robotics-simulation-engineer/lab-07-physics-identification.html>
- [NVIDIA Physics Simulation Fundamentals](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/physics/simulation_fundamentals.html)
- [NVIDIA Robot Simulation Tips](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/robot_simulation/robot_simulation_tips.html)
- Scorer: [lab-assets/score_parameter_sweep.py](lab-assets/score_parameter_sweep.py)

## Identification is not random tuning

```mermaid
flowchart LR
    Contract["Fixed scene + command"] --> Repeat["Repeat baseline"]
    Repeat --> Noise["Measure run variance"]
    Noise --> Sweep["Sweep one family"]
    Sweep --> Score["Score raw rows"]
    Score --> Holdout["Validate unseen episode"]
```

Parameter identification asks which values explain specified observations. Random tuning asks which values look acceptable once. Only the first supports review and later uncertainty bounds.

## Step 1 — declare one experiment

Use the Lab 03 TurtleBot response or a Lab 06 joint step. Freeze:

- USD stage and source hash;
- initial pose and reset method;
- physics step, render rate, and real-time mode;
- command waveform and duration;
- sensor/topic sampling method;
- GPU/driver/simulator build;
- metrics and acceptance thresholds.

Example outputs:

```text
stop_distance      [m]
yaw_error          [rad]
settling_time      [s]
peak_wheel_speed   [rad/s]
```

Use these exact names as CSV columns and contract keys; units live in the contract description, not in the column names.

## Step 2 — measure repeatability before changing parameters

Run the identical baseline at least five times. Compute mean, standard deviation, min, and max. If the between-run range is larger than the improvement you hope to measure, fix reset, timing, or observation first.

```mermaid
flowchart TD
    A["Baseline variation high"] --> B{"Initial state identical?"}
    B -->|No| C["Reset stage/state deterministically"]
    B -->|Yes| D{"Command and sampling share sim time?"}
    D -->|No| E["Fix timing ownership"]
    D -->|Yes| F{"Rendering/CPU load changes RTF?"}
    F -->|Yes| G["Separate sim-stamp metrics from wall metrics"]
```

## Step 3 — choose identifiable parameter families

| Symptom/metric | First parameter family | Confounders to hold fixed |
|---|---|---|
| stopping distance | dynamic friction, drive damping | mass, command, timestep |
| yaw response | wheel radius/separation, friction asymmetry | controller mapping |
| settling/overshoot | drive stiffness/damping | payload, timestep |
| impact bounce | restitution/compliant contact | collision geometry |
| penetration/jitter | timestep/solver iterations | collider and inertia validity |

Contact behavior combines both contacting materials. Record static/dynamic friction, restitution, compliant-contact settings, and combine modes on both surfaces.

## Step 4 — produce raw sweep rows

Use the provided CSV schema:

```csv
scenario_id,friction,damping,mass_scale,repeat,stop_distance,yaw_error,settling_time
```

A *candidate* is one combination of parameter values. Every column that is not `scenario_id`, `repeat`, `notes`, or a metric counts as a parameter. Change one parameter family per sweep, and run every candidate at least three times. Keep every raw row, not only the best-looking run.

The scorer enforces both rules:
- It rejects a sweep in which more than one parameter column varies, unless you declare those columns as one family with `--family`.
- It rejects any candidate with fewer than `--min-repeats` runs (default 3).

The shipped `fixtures/physics_sweep.csv` sweeps friction at 0.5, 0.7, and 0.9 with damping and mass fixed, three runs each.

## Step 5 — rank using a declared contract

```powershell
python "$Assets\score_parameter_sweep.py" "$Assets\fixtures\physics_sweep.csv" "$Assets\fixtures\physics_targets.json" `
  --family friction --holdout "$Assets\fixtures\physics_holdout.csv" --output "$Run\physics_fit.json"
```

Each run is scored as a weighted sum of absolute normalized errors:

```text
score = Σ weight_i × |observed_i - target_i| / scale_i
```

Candidates are ranked by their **mean** score over repeats, never by their luckiest single run. The report gives each candidate's mean, standard deviation, and standard error. It sets `identifiable: false` when another candidate is within two standard errors of the difference, and lists those candidates under `indistinguishable_from_selected`.

Write the targets, normalization scales, weights, pre-calibration `baseline`, and `holdout_targets` into the contract before looking at results. Otherwise the scoring rule can be tuned to select a preferred answer. Use `--calibration-only` while exploring; it reports a ranking but cannot pass the gate.

## Step 6 — challenge the candidate on a held-out episode

Do not validate with the same command used for calibration. Examples:

- calibrate on forward stop; validate on turning stop;
- calibrate with nominal payload; validate with a declared payload change;
- calibrate at one speed; validate at a second safe speed.

Run both the selected candidate and the contract's `baseline` parameters on the held-out episode, at least three times each, and pass the rows with `--holdout`. The held-out score uses `holdout_targets`.

The report's `holdout.ok` is true only when the baseline's mean held-out score exceeds the selected candidate's by more than two standard errors of the difference (`improvement > two_standard_errors`). If several parameter sets fit equally well, report non-identifiability rather than inventing precision.

On the shipped fixtures, friction 0.7 is selected (mean 0.40, SE 0.03). On the held-out turning stop it improves on the 0.5 baseline by 3.29 against a noise band of 0.25.

## Evidence and gate

Save experiment contract, baseline repetitions, raw sweep CSV, `$Run\physics_fit.json`, parameter provenance, held-out rows, and an explanation of remaining ambiguity.

**Gate:** proceed only when a nominal configuration improves held-out error beyond repeat variability without breaking Labs 01–06 contracts.

Next: [Lab 08 — Regression and CI](lab-08-regression-ci.md).
