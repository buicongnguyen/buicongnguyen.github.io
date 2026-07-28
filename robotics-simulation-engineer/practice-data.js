window.roboticsSimulationQuestionGroups = [
  {
    id: "models-frames",
    title: "Models and Frames",
    objective: "Validate frame chains, units, mass properties, joint structure, and collision representations.",
    moduleHref: "index.html#module-2",
    labHref: "../labs/index.html#urdf",
    questions: [
      {
        q: "A link looks correct but rotates unrealistically about an unexpected point. What should you inspect first?",
        choices: ["The visual material", "The inertial origin, center of mass, and inertia orientation", "The camera clipping range", "The ROS topic frequency"],
        answer: 1,
        why: "Visual geometry can be correct while an incorrect inertial frame produces wrong rotational dynamics."
      },
      {
        q: "In a URDF-style model, a revolute joint axis is normally expressed in which frame?",
        choices: ["The world frame", "The parent link inertial frame", "The joint frame established by the joint origin", "The child link visual frame"],
        answer: 2,
        why: "The joint origin establishes the joint frame, and the axis vector is interpreted in that frame."
      },
      {
        q: "Let T_A_B map coordinates from frame B into frame A. Given T_W_B and T_B_C, which expression maps C into W?",
        choices: ["T_W_B * T_B_C", "T_B_C * T_W_B", "inverse(T_W_B) * T_B_C", "T_W_B * inverse(T_B_C)"],
        answer: 0,
        why: "Transform composition follows the frame chain from C through B to W."
      },
      {
        q: "Which is the strongest basic validity check for the inertia tensor of a nondegenerate rigid body?",
        choices: ["Its diagonal entries are equal", "Its determinant is negative", "It is symmetric, has positive principal moments, and satisfies principal-moment triangle inequalities", "Its trace equals the body mass"],
        answer: 2,
        why: "A physical inertia tensor is symmetric and positive definite, with physically consistent principal moments."
      },
      {
        q: "A robot imported from a centimeter-based asset appears 100 times too large. What is the best correction?",
        choices: ["Move the camera farther away", "Correct units at import and revalidate geometry, translations, mass, and inertia", "Divide all controller gains by 100", "Increase contact solver iterations"],
        answer: 1,
        why: "Unit errors affect geometry and physical parameters, so they must be corrected consistently at the model boundary."
      },
      {
        q: "Why are simplified primitives or convex decompositions commonly used for moving-body collision geometry?",
        choices: ["They improve texture quality", "They eliminate the need for inertial properties", "They make collision detection faster and generally more stable", "They automatically identify friction coefficients"],
        answer: 2,
        why: "Detailed visual meshes often create costly or fragile contacts, while collision proxies preserve useful shape."
      },
      {
        q: "What does the parallel-axis theorem compute?",
        choices: ["Inertia about a parallel axis displaced from the center of mass", "The transform between two rotating cameras", "The friction force at a joint", "The velocity limit of an actuator"],
        answer: 0,
        why: "It shifts an inertia tensor between parallel axes using the mass and displacement from the center of mass."
      },
      {
        q: "A fixed-mounted camera becomes incorrectly oriented when upstream joints move. Which model data is most relevant?",
        choices: ["The camera image resolution", "The link color", "The contact restitution", "The fixed-joint transform chain and frame-axis conventions"],
        answer: 3,
        why: "An attachment error propagates through the kinematic chain as parent links move."
      },
      {
        q: "How should a closed kinematic loop usually be represented when the base robot-description format requires a tree?",
        choices: ["Duplicate every link in the loop", "Break the loop in the tree and add an explicit simulator-supported closure constraint", "Replace all revolute joints with fixed joints", "Increase the physics timestep"],
        answer: 1,
        why: "A tree representation needs an additional constraint to restore the physical loop without duplicating bodies."
      },
      {
        q: "What is the best way to validate a model converted between URDF, MJCF, USD, or SDF?",
        choices: ["Confirm only that both models render similarly", "Compare file sizes", "Run canonical tests for forward kinematics, limits, mass properties, and collision behavior", "Use identical parameter names in both files"],
        answer: 2,
        why: "Equivalent appearance does not prove equivalent kinematics, dynamics, or contacts."
      }
    ]
  },
  {
    id: "dynamics-contact-control",
    title: "Dynamics, Contact, and Control",
    objective: "Predict and measure timestep, contact, energy, actuator, and closed-loop response behavior.",
    moduleHref: "index.html#module-1",
    labHref: "../labs/index.html#calibration",
    questions: [
      {
        q: "What is the usual effect of halving the physics timestep while simulating the same duration?",
        choices: ["More integration work and often better numerical accuracy or stability", "Half as many solver steps with identical dynamics", "Higher restitution without additional cost", "Automatic correction of invalid inertia tensors"],
        answer: 0,
        why: "A smaller timestep requires more steps and can reduce discretization error, but it is not a universal repair."
      },
      {
        q: "A horizontal force below the static-friction limit is applied to a block that remains at rest. What is the friction force?",
        choices: ["Always zero", "Always equal to the maximum static friction", "Approximately equal and opposite to the applied force", "Equal to the kinetic-friction value"],
        answer: 2,
        why: "Static friction adjusts up to its limit to prevent relative motion."
      },
      {
        q: "What physical behavior is primarily controlled by the coefficient of restitution?",
        choices: ["Tangential sliding resistance", "Normal rebound speed after impact", "Joint motor saturation", "Sensor latency"],
        answer: 1,
        why: "Restitution describes how much relative normal velocity is recovered after a collision."
      },
      {
        q: "A stiff compliant contact model jitters and penetrates noticeably at a large timestep. What is the best response?",
        choices: ["Increase restitution to one", "Replace collision meshes with visual meshes", "Raise controller gains", "Reduce the timestep or add substeps, then retune contact stiffness and damping"],
        answer: 3,
        why: "Contact stiffness, damping, effective mass, and timestep must be numerically compatible."
      },
      {
        q: "What is a realistic consequence of increasing constraint-solver iterations?",
        choices: ["Constraint error may decrease, but computation cost rises", "All contacts become perfectly accurate", "Invalid joint axes are repaired", "Rendering becomes the only bottleneck"],
        answer: 0,
        why: "Additional iterations can improve convergence but cannot compensate for an invalid model."
      },
      {
        q: "A high-gain position controller oscillates after one control-cycle delay is introduced. What is the most defensible first adjustment?",
        choices: ["Increase proportional gain further", "Increase object restitution", "Reduce gains or add damping while modeling the delay explicitly", "Use a more detailed visual mesh"],
        answer: 2,
        why: "Delay reduces phase margin, so aggressive gains that were stable without delay may become unstable."
      },
      {
        q: "For a single degree of freedom with stiffness k and effective mass m, what damping is approximately critical?",
        choices: ["k / m", "2 * sqrt(k * m)", "sqrt(k) / (2 * m)", "2 * k * m"],
        answer: 1,
        why: "The standard second-order critical-damping coefficient is 2 times the square root of stiffness times mass."
      },
      {
        q: "Which technique directly addresses integral windup when an actuator saturates?",
        choices: ["Increasing the visual update rate", "Disabling joint limits", "Raising the integral gain", "Clamping or back-calculating the integral state"],
        answer: 3,
        why: "Anti-windup prevents the integrator from accumulating error that the saturated actuator cannot correct."
      },
      {
        q: "A controller tracks well in free space but fails while lifting an object. What should be checked first?",
        choices: ["Applied actuator effort limits and saturation under load", "The background texture", "The camera field of view", "The names of unused links"],
        answer: 0,
        why: "Contact and payload forces may demand more torque than the actuator model can apply."
      },
      {
        q: "What result should an energy audit expect from an unforced passive system with damping?",
        choices: ["Mechanical energy must increase linearly", "Energy must remain exactly constant through every impact", "Mechanical energy should not show systematic unphysical growth", "Potential energy must always be zero"],
        answer: 2,
        why: "Damping and inelastic contact can dissipate energy, but a passive model should not create it persistently."
      }
    ]
  },
  {
    id: "simulators-performance",
    title: "Simulators and Performance",
    objective: "Design fair simulator experiments and isolate physics, rendering, reset, and host/device bottlenecks.",
    moduleHref: "index.html#module-9",
    labHref: "../labs/index.html#benchmark",
    questions: [
      {
        q: "What does a real-time factor of 2.0 mean?",
        choices: ["Two wall-clock seconds pass per simulated second", "The simulation advances two simulated seconds per wall-clock second", "Physics runs at twice the sensor frequency", "The timestep is two seconds"],
        answer: 1,
        why: "Real-time factor is simulated elapsed time divided by wall-clock elapsed time."
      },
      {
        q: "Which procedure gives the fairest GPU simulation benchmark?",
        choices: ["Time only the fastest iteration", "Include asset loading in some trials but not others", "Change sensor settings until every system reaches the same result", "Warm up, fix the workload, synchronize around timing, repeat, and report configuration"],
        answer: 3,
        why: "Warmup, controlled workload, synchronization, and repeated measurements reduce timing bias."
      },
      {
        q: "Why can camera-enabled simulation remain expensive in headless mode?",
        choices: ["Sensor render products may still execute even without a visible UI", "Headless mode forces all physics onto the CPU", "A camera disables collision broadphase", "Headless mode doubles every mesh"],
        answer: 0,
        why: "Removing the window does not necessarily remove sensor rendering or readback work."
      },
      {
        q: "Throughput stops improving when scaling from 256 to 1024 environments. What is the best next step?",
        choices: ["Assume the simulator cannot scale", "Increase every solver parameter", "Profile GPU occupancy, memory use, synchronization, sensors, and host-device transfers", "Reduce all robot masses"],
        answer: 2,
        why: "Scaling can plateau for several distinct resource or synchronization reasons that profiling can separate."
      },
      {
        q: "A Python loop updates each environment independently and dominates step time. What is the preferred optimization?",
        choices: ["Add more log statements", "Replace the loop with batched array or tensor operations", "Increase render resolution", "Use unique physics settings for every environment"],
        answer: 1,
        why: "Batched operations reduce interpreter overhead and better utilize parallel hardware."
      },
      {
        q: "What generally makes large-scale environment resets more efficient?",
        choices: ["Reloading every asset from disk", "Rebuilding the entire scene graph", "Creating a new simulator process per episode", "Preallocating assets and batching state updates"],
        answer: 3,
        why: "Reusing scene structure avoids expensive allocation, parsing, and synchronization work."
      },
      {
        q: "What is the purpose of collision broadphase?",
        choices: ["Quickly reject body pairs that cannot be touching before detailed contact tests", "Compute final contact impulses exactly", "Render collision geometry", "Tune actuator gains"],
        answer: 0,
        why: "Broadphase reduces the number of pairs sent to more expensive narrow-phase collision checks."
      },
      {
        q: "What usually happens when physics substeps are increased while the outer simulation step remains fixed?",
        choices: ["Fewer constraint solves are performed", "Sensor noise disappears", "Contact resolution may improve at the cost of lower throughput", "Robot geometry is simplified automatically"],
        answer: 2,
        why: "More substeps resolve dynamics at finer intervals but require additional computation."
      },
      {
        q: "Why might two runs differ slightly despite using the same random seed?",
        choices: ["Random seeds control mesh topology", "Parallel scheduling and floating-point reduction order can remain nondeterministic", "A seed disables contact mechanics", "Identical seeds always guarantee bitwise equality"],
        answer: 1,
        why: "A seed controls random sampling but not every source of parallel numerical nondeterminism."
      },
      {
        q: "What is the strongest method for comparing physics behavior across two simulators?",
        choices: ["Copy all low-level solver numbers directly", "Compare only screenshots", "Require identical internal contact algorithms", "Run the same canonical experiments and compare observable metrics"],
        answer: 3,
        why: "Equivalent tests and measured outputs are more meaningful than simulator-specific parameter names."
      }
    ]
  },
  {
    id: "ros2-sensors-pipelines",
    title: "ROS 2, Sensors, and Pipelines",
    objective: "Specify and validate time, frame, QoS, sensor, watchdog, and replay contracts.",
    moduleHref: "index.html#module-5",
    labHref: "../labs/index.html#readiness",
    questions: [
      {
        q: "Sensor messages arrive, but TF lookup reports extrapolation errors. What is the most likely first issue to inspect?",
        choices: ["Collision friction", "Visual mesh complexity", "Timestamp consistency and the selected time source", "Actuator effort limits"],
        answer: 2,
        why: "TF queries fail when message stamps and available transforms refer to incompatible times."
      },
      {
        q: "How should ROS 2 nodes normally behave when connected to a simulator that publishes a simulation clock?",
        choices: ["Use the simulation time source consistently", "Mix wall time and simulation time per topic", "Ignore message timestamps", "Publish transforms only at startup"],
        answer: 0,
        why: "A consistent simulated clock keeps sensors, transforms, controllers, and replay aligned."
      },
      {
        q: "A publisher is visible in the ROS graph, but a subscriber receives no messages. What should be checked first at the transport level?",
        choices: ["Robot mass", "Camera intrinsics", "Joint damping", "Publisher and subscriber QoS compatibility"],
        answer: 3,
        why: "Incompatible requested and offered QoS policies can prevent endpoint communication."
      },
      {
        q: "What is the conventional axis orientation of a ROS camera optical frame?",
        choices: ["X forward, Y left, Z up", "X right, Y down, Z forward", "X left, Y up, Z backward", "X up, Y forward, Z right"],
        answer: 1,
        why: "The optical-frame convention uses Z forward, X right, and Y down."
      },
      {
        q: "Why must an IMU simulator document whether gravity is included in accelerometer output?",
        choices: ["Gravity changes image resolution", "Gravity determines ROS QoS", "Accelerometers measure specific force, and APIs differ in how gravity is represented", "Gravity affects only LiDAR"],
        answer: 2,
        why: "Consumers need a clear convention to avoid adding or removing gravity twice."
      },
      {
        q: "Independent Gaussian noise is added to every IMU sample, but long-term drift is still unrealistically small. What is missing?",
        choices: ["Bias instability or random-walk behavior", "A higher camera frame rate", "Convex collision geometry", "A larger joint effort limit"],
        answer: 0,
        why: "White noise models short-term variation, while slowly changing bias produces accumulated drift."
      },
      {
        q: "Which timestamp should a delayed camera message normally carry for sensor fusion?",
        choices: ["The time the consumer receives it", "The next controller update time", "Zero", "The image acquisition time"],
        answer: 3,
        why: "Fusion should associate the measurement with the robot state at acquisition, not publication or receipt."
      },
      {
        q: "A heavy perception callback blocks command handling and creates growing latency. What is the best architectural response?",
        choices: ["Increase all controller gains", "Separate the work using bounded queues, executors, or worker threads", "Remove timestamps", "Publish larger images"],
        answer: 1,
        why: "Decoupling expensive work prevents one callback from starving time-sensitive control processing."
      },
      {
        q: "What should a simulated robot do when command messages stop arriving unexpectedly?",
        choices: ["Repeat the last command forever", "Disable joint limits", "Use a timeout watchdog that transitions to a defined safe state", "Increase simulation speed"],
        answer: 2,
        why: "A watchdog makes stale-command behavior explicit and safer for both simulation and hardware."
      },
      {
        q: "What should be captured to make a ROS-based simulation run meaningfully replayable?",
        choices: ["Topic data, clock, transforms, parameters, configuration, and software revision", "Only the final camera frame", "Only terminal output", "The robot visual mesh but no timestamps"],
        answer: 0,
        why: "Replay requires both time-aligned data and the configuration that gave those messages meaning."
      }
    ]
  },
  {
    id: "sim-to-real-debugging-ci",
    title: "Sim-to-Real, Debugging, and CI",
    objective: "Separate calibration, uncertainty, causal diagnosis, reproducibility, and production evidence.",
    moduleHref: "index.html#module-7",
    labHref: "../labs/index.html#determinism",
    questions: [
      {
        q: "Why should system-identification parameters be evaluated on held-out trajectories?",
        choices: ["To increase render quality", "To detect overfitting and test whether the parameters generalize", "To remove the need for excitation", "To guarantee the model is physically unique"],
        answer: 1,
        why: "Parameters that fit calibration data may still fail under different motions or contacts."
      },
      {
        q: "How should domain-randomization ranges ideally be chosen?",
        choices: ["Make every parameter vary over its mathematically possible range", "Randomize only visual colors", "Use the same percentage for every parameter", "Base distributions on identified uncertainty, measurements, and sensitivity"],
        answer: 3,
        why: "Realistic uncertainty targets transfer better than indiscriminately broad randomization."
      },
      {
        q: "A policy succeeds by rapidly vibrating a gripper against an object, a behavior unlikely to work on hardware. What does this suggest?",
        choices: ["The policy may be exploiting contact or reward-model artifacts", "The URDF must be visually incorrect", "The camera resolution is too low", "The benchmark needs fewer seeds"],
        answer: 0,
        why: "Unphysical high-frequency behavior is a common sign of simulator or reward exploitation."
      },
      {
        q: "A controller is stable in simulation but oscillates on hardware with a clear phase lag. Which missing effect should be investigated first?",
        choices: ["Texture compression", "Collision color", "Sensing, communication, and actuator latency", "The number of README sections"],
        answer: 2,
        why: "Unmodeled delay reduces control stability margins and can explain the observed phase lag."
      },
      {
        q: "An imported robot explodes on the first physics step. What is the most efficient initial debugging approach?",
        choices: ["Start reinforcement learning immediately", "Disable controllers and isolate units, overlaps, joint transforms, and inertial validity", "Increase every solver iteration limit", "Replace all collisions with detailed triangle meshes"],
        answer: 1,
        why: "Removing active control and checking basic model invariants isolates common catastrophic causes quickly."
      },
      {
        q: "What belongs in a fast headless simulation CI smoke test?",
        choices: ["Manual visual inspection", "A full multi-day training run", "Pixel-perfect screenshots across all GPUs", "Startup, several deterministic steps, finite-state checks, bounds, and clean shutdown"],
        answer: 3,
        why: "A smoke test should cheaply catch broken assets, APIs, NaNs, invalid states, and lifecycle failures."
      },
      {
        q: "A numerical simulation test fails occasionally because of small parallel floating-point differences. What is the best response?",
        choices: ["Use physically justified tolerances and evaluate repeated-run invariants or distributions", "Delete the test", "Require exact bitwise equality everywhere", "Disable all logging"],
        answer: 0,
        why: "Robust tests distinguish meaningful regressions from harmless numerical ordering differences."
      },
      {
        q: "How should a CI performance regression be measured most credibly?",
        choices: ["Compare one un-warmed iteration on arbitrary machines", "Use the developer's memory of prior speed", "Use repeated warm measurements on controlled hardware and compare robust statistics", "Fail whenever any timing differs"],
        answer: 2,
        why: "Controlled repeated measurements make thresholds less sensitive to startup and machine noise."
      },
      {
        q: "A project uses one simulator as a reference but has no physical robot measurements. How should its transfer result be described?",
        choices: ["Proven real-world deployment", "Sim-to-sim robustness or cross-simulator validation", "Hardware-certified dynamics", "Guaranteed sim-to-real transfer"],
        answer: 1,
        why: "Without physical measurements, sim-to-real claims would exceed the available evidence."
      },
      {
        q: "Which metadata best supports reproducible simulation experiments?",
        choices: ["Only the experiment title", "Only the final success rate", "Only the robot asset filename", "Commit ID, config hash, seed, environment, hardware, commands, and output artifacts"],
        answer: 3,
        why: "Complete provenance connects a result to the exact code, inputs, execution context, and evidence."
      }
    ]
  }
];
