(function () {
  "use strict";

  function readSaved(storageKey) {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey) || "[]");
      return Array.isArray(value) ? value : [];
    } catch (_error) {
      return [];
    }
  }

  function writeSaved(storageKey, ids) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(ids));
    } catch (_error) {
      // The course remains usable when storage is blocked.
    }
  }

  function setupTracker(config) {
    const checks = Array.from(document.querySelectorAll(config.selector));
    const bar = document.getElementById(config.barId);
    const count = document.getElementById(config.countId);
    const reset = document.getElementById(config.resetId);
    if (!checks.length || !bar || !count || !reset) return;

    function updateProgress(save) {
      const completed = checks.filter(function (checkbox) {
        return checkbox.checked;
      });
      const percentage = Math.round((completed.length / checks.length) * 100);

      bar.value = percentage;
      bar.textContent = percentage + "%";
      count.textContent = completed.length + " / " + checks.length + " " + config.unit + " · " + percentage + "%";

      checks.forEach(function (checkbox) {
        const card = checkbox.closest(config.cardSelector);
        if (card) card.classList.toggle("is-complete", checkbox.checked);
      });

      if (save) {
        writeSaved(config.storageKey, completed.map(function (checkbox) {
          return checkbox.value;
        }));
      }
    }

    const saved = readSaved(config.storageKey);
    checks.forEach(function (checkbox) {
      checkbox.checked = saved.includes(checkbox.value);
      checkbox.addEventListener("change", function () {
        updateProgress(true);
      });
    });

    reset.addEventListener("click", function () {
      if (!checks.some(function (checkbox) { return checkbox.checked; })) return;
      checks.forEach(function (checkbox) {
        checkbox.checked = false;
      });
      updateProgress(true);
    });

    updateProgress(false);
  }

  // Keep the execution order calibration → uncertainty randomization while
  // preserving stable module IDs for saved progress and inbound links.
  const calibrationModule = document.getElementById("module-7");
  const randomizationModule = document.getElementById("module-8");
  if (
    calibrationModule &&
    randomizationModule &&
    calibrationModule.parentElement === randomizationModule.parentElement
  ) {
    calibrationModule.parentElement.insertBefore(calibrationModule, randomizationModule);
  }

  setupTracker({
    selector: "[data-module-check]",
    storageKey: "robotics-simulation-engineer-course-v1",
    barId: "course-progress-bar",
    countId: "course-progress-count",
    resetId: "course-progress-reset",
    unit: "modules",
    cardSelector: ".module"
  });

  setupTracker({
    selector: "[data-sprint-check]",
    storageKey: "robotics-simulation-engineer-sprint-v1",
    barId: "sprint-progress-bar",
    countId: "sprint-progress-count",
    resetId: "sprint-progress-reset",
    unit: "days",
    cardSelector: "tr"
  });
}());
