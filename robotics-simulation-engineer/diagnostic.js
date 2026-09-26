(function () {
  "use strict";
  const form = document.getElementById("diagnostic-form");
  const output = document.getElementById("diagnostic-result");
  if (!form || !output) return;
  const key = "robotics-simulation-entry-diagnostic-v1";
  // Core prerequisites gate simulator work. The other three domains are taught inside the
  // course, so a gap there changes emphasis, never the starting point: placement must not
  // send a learner with fewer passes further into the book than a learner with more.
  const coreDomains = ["python", "git", "transforms", "dynamics"];
  const readiness = { label: "the readiness lab", href: "../labs/index.html#readiness" };
  const emphasisByDomain = {
    models: "Module 2 (URDF-to-USD model engineering)",
    ros: "Module 5 (ROS 2 and sensors) and Labs 01–05",
    statistics: "Module 6 (evaluation) and Module 7 (calibration)"
  };
  const coreLabels = {
    python: "Python, NumPy, and pytest",
    git: "Git and command line",
    transforms: "linear algebra and transform composition",
    dynamics: "inertia and step-response fundamentals"
  };

  function save() {
    const state = {};
    form.querySelectorAll('input[type="checkbox"]').forEach((box) => { state[box.name] = box.checked; });
    try { localStorage.setItem(key, JSON.stringify(state)); } catch (_error) { /* diagnostic remains usable */ }
  }

  function restore() {
    try {
      const state = JSON.parse(localStorage.getItem(key) || "{}");
      if (!state || typeof state !== "object" || Array.isArray(state)) return;
      Object.entries(state).forEach(([name, checked]) => {
        const box = form.elements[name];
        if (box) box.checked = checked === true;
      });
    } catch (_error) { /* ignore invalid saved state */ }
  }

  // Exposed for tests: returns the route, the reason, where to start, and what to emphasize.
  function place(passedNames) {
    const passed = new Set(passedNames);
    const missingCore = coreDomains.filter((domain) => !passed.has(domain));
    const emphasis = Object.keys(emphasisByDomain).filter((domain) => !passed.has(domain)).map((domain) => emphasisByDomain[domain]);
    if (missingCore.length) {
      return {
        route: "Foundation route (10–14 weeks)",
        reason: "A core prerequisite is missing (" + missingCore.map((domain) => coreLabels[domain]).join(", ") + "), so complete the entry gate before simulator work.",
        start: { label: "Start " + readiness.label, href: readiness.href },
        emphasis: emphasis
      };
    }
    if (passed.size === 7) {
      return {
        route: "14-day portfolio sprint, or the 4–6 week experienced route",
        reason: "Every prerequisite has observable evidence.",
        start: { label: "Begin Day 1 of the 14-day sprint", href: "index.html#fast-track" },
        emphasis: emphasis
      };
    }
    const experienced = passed.size >= 5;
    return {
      route: experienced ? "Experienced route (4–6 weeks)" : "Foundation route (10–14 weeks), paced from Module 0",
      reason: "The core gate is complete. Start at Module 0 like everyone else and go deeper where the diagnostic found gaps.",
      start: { label: "Begin Module 0", href: "index.html#module-0" },
      emphasis: emphasis
    };
  }
  window.roboticsPlacement = place;

  form.addEventListener("change", save);
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const boxes = Array.from(form.querySelectorAll('input[type="checkbox"]'));
    const passed = boxes.filter((box) => box.checked).map((box) => box.name);
    const placement = place(passed);
    output.innerHTML = "";
    const heading = document.createElement("h3");
    heading.textContent = passed.length + " / " + boxes.length + " passed · " + placement.route;
    output.appendChild(heading);
    const text = document.createElement("p");
    text.textContent = placement.reason + (placement.emphasis.length
      ? " Go deeper in: " + placement.emphasis.join("; ") + "."
      : "");
    output.appendChild(text);
    const link = document.createElement("a");
    link.href = placement.start.href;
    link.textContent = placement.start.label;
    output.appendChild(link);
    save();
  });
  form.addEventListener("reset", function () {
    try { localStorage.removeItem(key); } catch (_error) { /* ignore */ }
    setTimeout(() => { output.innerHTML = "<p>Complete the tasks, then calculate your placement.</p>"; }, 0);
  });
  restore();
}());
