(function () {
  "use strict";
  const form = document.getElementById("diagnostic-form");
  const output = document.getElementById("diagnostic-result");
  if (!form || !output) return;
  const key = "robotics-simulation-entry-diagnostic-v1";
  const remediationByDomain = {
    python: { order: 0, label: "Entry gate: Python, NumPy, and pytest", href: "../labs/index.html#readiness" },
    git: { order: 0, label: "Entry gate: Git and command line", href: "../labs/index.html#readiness" },
    transforms: { order: 0, label: "Entry gate: linear algebra and transform composition", href: "../labs/index.html#readiness" },
    dynamics: { order: 0, label: "Entry gate: inertia and step-response fundamentals", href: "../labs/index.html#readiness" },
    models: { order: 2, label: "Module 2: URDF-to-USD model engineering", href: "index.html#module-2" },
    ros: { order: 5, label: "Module 5: ROS 2 and sensors", href: "index.html#module-5" },
    statistics: { order: 6, label: "Module 6 evaluation, then Module 7 calibration", href: "index.html#module-6" }
  };
  const coreDomains = ["python", "git", "transforms", "dynamics"];

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

  form.addEventListener("change", save);
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const boxes = Array.from(form.querySelectorAll('input[type="checkbox"]'));
    const passed = boxes.filter((box) => box.checked);
    const weakDomains = boxes.filter((box) => !box.checked).map((box) => box.name);
    const weak = weakDomains
      .map((domain) => remediationByDomain[domain])
      .sort((left, right) => left.order - right.order);
    const corePassed = coreDomains.every((domain) => form.elements[domain].checked);
    let route = "Foundation route (10–14 weeks)";
    let reason = corePassed
      ? "Build the remaining prerequisites before simulator work."
      : "A core prerequisite is missing, so complete the entry gate before simulator work.";
    if (passed.length === 7) {
      route = "14-day portfolio sprint or 4–6 week experienced route";
      reason = "Every prerequisite has observable evidence.";
    } else if (passed.length >= 5 && corePassed) {
      route = "Experienced route (4–6 weeks), beginning at the first weak domain";
      reason = "The core gate is complete; remediate the remaining domain in sequence.";
    }
    output.innerHTML = "";
    const heading = document.createElement("h3");
    heading.textContent = passed.length + " / 7 passed · " + route;
    output.appendChild(heading);
    const text = document.createElement("p");
    text.textContent = weak.length
      ? reason + " Recommended work: " + weak.map((item) => item.label).join("; ") + "."
      : "All prerequisites are demonstrated. Begin Module 0 and retain the diagnostic evidence.";
    output.appendChild(text);
    const link = document.createElement("a");
    link.href = weak.length ? weak[0].href : "index.html#module-0";
    link.textContent = weak.length ? "Start the first remediation" : "Begin Module 0";
    output.appendChild(link);
    save();
  });
  form.addEventListener("reset", function () {
    try { localStorage.removeItem(key); } catch (_error) { /* ignore */ }
    setTimeout(() => { output.innerHTML = "<p>Complete the tasks, then calculate your placement.</p>"; }, 0);
  });
  restore();
}());
