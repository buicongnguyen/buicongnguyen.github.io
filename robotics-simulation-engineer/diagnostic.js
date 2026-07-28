(function () {
  "use strict";
  const form = document.getElementById("diagnostic-form");
  const output = document.getElementById("diagnostic-result");
  if (!form || !output) return;
  const key = "robotics-simulation-entry-diagnostic-v1";
  const moduleByDomain = {
    python: "Module 0 readiness: Python/NumPy/pytest",
    git: "Module 0 readiness: Git and CLI",
    transforms: "Module 3: robot models and frames",
    dynamics: "Module 2: dynamics, then Module 5 control",
    ros: "Module 6: ROS 2 and sensors",
    statistics: "Module 7 evaluation, then Module 8 calibration",
    models: "Module 3: URDF-to-USD model engineering"
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

  form.addEventListener("change", save);
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const boxes = Array.from(form.querySelectorAll('input[type="checkbox"]'));
    const passed = boxes.filter((box) => box.checked);
    const weak = boxes.filter((box) => !box.checked).map((box) => moduleByDomain[box.name]);
    let route = "Foundation route (10–14 weeks)";
    if (passed.length === 7) route = "14-day portfolio sprint or 4–6 week experienced route";
    else if (passed.length >= 5) route = "Experienced route (4–6 weeks), beginning at the first weak domain";
    output.innerHTML = "";
    const heading = document.createElement("h3");
    heading.textContent = passed.length + " / 7 passed · " + route;
    output.appendChild(heading);
    const text = document.createElement("p");
    text.textContent = weak.length ? "Recommended starting work: " + weak.join("; ") + "." : "All prerequisites are demonstrated. Begin Module 1 and retain the diagnostic evidence.";
    output.appendChild(text);
    const link = document.createElement("a");
    link.href = "dashboard.html#module-map";
    link.textContent = "Open your module map";
    output.appendChild(link);
    save();
  });
  form.addEventListener("reset", function () {
    try { localStorage.removeItem(key); } catch (_error) { /* ignore */ }
    setTimeout(() => { output.innerHTML = "<p>Complete the tasks, then calculate your placement.</p>"; }, 0);
  });
  restore();
}());
