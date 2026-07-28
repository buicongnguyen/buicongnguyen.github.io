(function () {
  "use strict";

  const groups = window.roboticsSimulationQuestionGroups || [];
  const storageKey = "robotics-simulation-engineer-practice-v1";
  const historyKey = "robotics-simulation-engineer-assessment-history-v1";
  const modeKey = "robotics-simulation-engineer-assessment-mode-v1";
  const allowedModes = new Set(["practice", "pre-test", "post-test"]);
  const root = document.getElementById("questions-root");
  const search = document.getElementById("question-search");
  const category = document.getElementById("question-category");
  const stats = document.getElementById("quiz-stats");
  const objectiveScores = document.getElementById("objective-scores");
  const modeLabel = document.getElementById("assessment-mode");
  let assessmentMode = "practice";
  try {
    const savedMode = localStorage.getItem(modeKey);
    if (allowedModes.has(savedMode)) assessmentMode = savedMode;
  } catch (_error) { /* use practice */ }
  const intros = {
    "models-frames": "Kinematic trees, transform conventions, mass properties, collision geometry, and model conversion.",
    "dynamics-contact-control": "Timestep, constraints, friction, restitution, actuator limits, delay, control, and energy.",
    "simulators-performance": "Benchmark design, headless sensors, batching, reset cost, determinism, and cross-simulator comparison.",
    "ros2-sensors-pipelines": "Clock, TF, QoS, sensor conventions, noise, callback architecture, watchdogs, and replay.",
    "sim-to-real-debugging-ci": "Identification, randomization, artifact exploitation, failure isolation, tolerances, provenance, and CI."
  };
  const confirmationByGroup = {
    "models-frames": "Query the frame/mass properties, visualize axes and COM, then run a canonical FK or joint-sweep check.",
    "dynamics-contact-control": "Freeze the model and controller, sweep one timestep/contact/control variable, and compare the predicted trace quantity.",
    "simulators-performance": "Use matched workload, warmup, synchronization, and hardware; change one subsystem and retain a profiler trace.",
    "ros2-sensors-pipelines": "Inspect topic type/QoS, TF at the acquisition stamp, /clock, achieved rate, and a short rosbag capture.",
    "sim-to-real-debugging-ci": "Freeze identity, run a discriminating held-out or injected-fault experiment, and retain raw evidence plus the decision threshold."
  };

  function sanitizeResults(parsed) {
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const questionById = {};
    groups.forEach(function (group) {
      group.questions.forEach(function (question, index) {
        questionById[questionId(group, index)] = question;
      });
    });
    const clean = {};
    Object.entries(parsed).forEach(function (entry) {
      const id = entry[0];
      const value = entry[1];
      const question = questionById[id];
      if (
        !question ||
        !value ||
        typeof value !== "object" ||
        Array.isArray(value) ||
        !Number.isInteger(value.selected) ||
        value.selected < 0 ||
        value.selected >= question.choices.length
      ) return;
      const checked = value.checked !== false;
      clean[id] = {
        selected: value.selected,
        // Derive correctness from authoritative question data; never trust a
        // persisted score flag that can be stale or malformed.
        correct: checked && value.selected === question.answer,
        checked: checked,
        mode: allowedModes.has(value.mode) ? value.mode : "practice",
        attemptedAt: Number.isFinite(value.attemptedAt) && value.attemptedAt >= 0 ? value.attemptedAt : null,
        reviewStage: Number.isInteger(value.reviewStage) && value.reviewStage >= 0 && value.reviewStage <= 3 ? value.reviewStage : 0,
        nextReview: Number.isFinite(value.nextReview) && value.nextReview >= 0 ? value.nextReview : null
      };
    });
    return clean;
  }

  function readResults() {
    try {
      return sanitizeResults(JSON.parse(localStorage.getItem(storageKey) || "{}"));
    } catch (_error) {
      return {};
    }
  }

  function readHistory() {
    try {
      const parsed = JSON.parse(localStorage.getItem(historyKey) || "{}");
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
      const clean = {};
      allowedModes.forEach(function (mode) {
        const assessment = parsed[mode];
        if (!assessment || typeof assessment !== "object" || Array.isArray(assessment)) return;
        clean[mode] = {
          savedAt: Number.isFinite(assessment.savedAt) ? assessment.savedAt : null,
          results: sanitizeResults(assessment.results)
        };
      });
      return clean;
    } catch (_error) {
      return {};
    }
  }

  let results = readResults();

  function saveResults() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(results));
    } catch (_error) {
      // Practice still works when browser storage is unavailable.
    }
  }

  function make(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function questionId(group, index) {
    return group.id + "-" + (index + 1);
  }

  function clearVisualResult(card) {
    card.classList.remove("is-answered");
    card.querySelectorAll(".choice").forEach(function (choice) {
      choice.classList.remove("is-correct", "is-wrong");
    });
    const feedback = card.querySelector(".feedback");
    feedback.className = "feedback";
    feedback.textContent = "Choose one answer, then check your reasoning.";
  }

  function applyResult(card, group, question, selected) {
    clearVisualResult(card);
    const choices = card.querySelectorAll(".choice");
    choices[question.answer].classList.add("is-correct");
    const correct = selected === question.answer;
    if (!correct && choices[selected]) choices[selected].classList.add("is-wrong");

    const feedback = card.querySelector(".feedback");
    feedback.classList.add(correct ? "is-correct" : "is-wrong");
    feedback.textContent = "";
    const structure = make("div", "feedback-structure");
    const strongest = make("p", "", (correct ? "Correct. " : "Correct answer: " + String.fromCharCode(65 + question.answer) + ". ") + "Why it is strongest: " + question.why);
    structure.appendChild(strongest);
    if (!correct) {
      structure.appendChild(make("p", "", "Why the selected distractor is weaker: “" + question.choices[selected] + "” addresses the wrong contract, skips a required boundary check, or makes a stronger claim than the available evidence supports."));
    }
    structure.appendChild(make("p", "", "Confirm with: " + confirmationByGroup[group.id]));
    structure.appendChild(make("p", "", "Objective: " + group.objective));
    const remediation = make("p", "", "Remediation: ");
    remediation.appendChild(linkNode(group.moduleHref, "review the exact course objective"));
    remediation.appendChild(document.createTextNode(" · "));
    remediation.appendChild(linkNode(group.labHref, "perform the linked lab"));
    structure.appendChild(remediation);
    feedback.appendChild(structure);
    card.classList.add("is-answered");
    return correct;
  }

  function linkNode(href, text) {
    const link = make("a", "", text);
    link.href = href;
    return link;
  }

  function renderQuestion(group, question, index, absoluteNumber) {
    const id = questionId(group, index);
    const card = make("details", "question-card");
    card.dataset.category = group.id;
    card.dataset.questionId = id;
    card.dataset.search = (group.title + " " + question.q + " " + question.choices.join(" ") + " " + question.why).toLowerCase();

    const summary = document.createElement("summary");
    const title = make("span", "question-title");
    title.appendChild(make("span", "question-number", absoluteNumber + ". "));
    title.appendChild(document.createTextNode(question.q));
    summary.appendChild(title);
    summary.appendChild(make("span", "question-tag", group.title));
    card.appendChild(summary);

    const body = make("div", "question-body");
    const fieldset = document.createElement("fieldset");
    fieldset.appendChild(make("legend", "", question.q));
    const list = make("div", "choice-list");

    question.choices.forEach(function (choiceText, choiceIndex) {
      const label = make("label", "choice");
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "answer-" + id;
      radio.value = String(choiceIndex);
      radio.addEventListener("change", function () {
        const previous = results[id] || {};
        results[id] = {
          selected: choiceIndex,
          correct: false,
          checked: false,
          mode: assessmentMode,
          attemptedAt: previous.attemptedAt || null,
          reviewStage: previous.reviewStage || 0,
          nextReview: previous.nextReview || null
        };
        saveResults();
        clearVisualResult(card);
        updateStats();
      });
      label.appendChild(radio);
      label.appendChild(make("span", "", String.fromCharCode(65 + choiceIndex) + ". " + choiceText));
      list.appendChild(label);
    });

    fieldset.appendChild(list);
    body.appendChild(fieldset);

    const actions = make("div", "question-actions");
    const check = make("button", "check-answer", "Check answer");
    check.type = "button";
    const feedback = make("p", "feedback", "Choose one answer, then check your reasoning.");
    feedback.setAttribute("aria-live", "polite");
    check.addEventListener("click", function () {
      const selected = card.querySelector("input[type=radio]:checked");
      if (!selected) {
        feedback.className = "feedback is-wrong";
        feedback.textContent = "Choose an answer before checking.";
        return;
      }
      const selectedIndex = Number(selected.value);
      const correct = applyResult(card, group, question, selectedIndex);
      const previous = results[id] || {};
      const reviewStage = correct ? Math.min((previous.reviewStage || 0) + 1, 3) : 0;
      const delays = [1, 3, 7];
      const nextReview = correct ? Date.now() + delays[Math.max(0, reviewStage - 1)] * 86400000 : Date.now();
      results[id] = { selected: selectedIndex, correct: correct, checked: true, mode: assessmentMode, attemptedAt: Date.now(), reviewStage: reviewStage, nextReview: nextReview };
      saveResults();
      updateStats();
    });
    actions.appendChild(check);
    actions.appendChild(feedback);
    body.appendChild(actions);
    card.appendChild(body);

    const saved = results[id];
    if (saved && Number.isInteger(saved.selected) && saved.selected >= 0 && saved.selected < question.choices.length) {
      const radio = card.querySelector('input[value="' + saved.selected + '"]');
      radio.checked = true;
      if (saved.checked !== false) applyResult(card, group, question, saved.selected);
    }

    return card;
  }

  function render() {
    let number = 0;
    groups.forEach(function (group) {
      const section = make("section", "quiz-group");
      section.id = group.id;
      section.dataset.group = group.id;
      section.appendChild(make("h3", "", group.title));
      section.appendChild(make("p", "", intros[group.id] || ""));
      section.appendChild(make("p", "section-note", "Objective: " + group.objective));

      group.questions.forEach(function (question, index) {
        number += 1;
        section.appendChild(renderQuestion(group, question, index, number));
      });
      root.appendChild(section);

      const option = document.createElement("option");
      option.value = group.id;
      option.textContent = group.title;
      category.appendChild(option);
    });
  }

  function updateStats() {
    const cards = Array.from(document.querySelectorAll(".question-card"));
    const visible = cards.filter(function (card) { return !card.classList.contains("hidden"); }).length;
    const validIds = new Set(cards.map(function (card) { return card.dataset.questionId; }));
    const resultEntries = Object.entries(results).filter(function (entry) {
      return validIds.has(entry[0]) && entry[1].checked !== false;
    });
    const correct = resultEntries.filter(function (entry) { return entry[1].correct; }).length;
    stats.textContent = visible + " of " + cards.length + " questions shown · " + resultEntries.length + " answered · " + correct + " correct";
    modeLabel.textContent = "Mode: " + assessmentMode;
    objectiveScores.textContent = "";
    let pretestResults = {};
    const history = readHistory();
    const savedPretest = history["pre-test"];
    if (
      savedPretest &&
      typeof savedPretest === "object" &&
      savedPretest.results &&
      typeof savedPretest.results === "object" &&
      !Array.isArray(savedPretest.results)
    ) pretestResults = savedPretest.results;
    groups.forEach(function (group) {
      const groupCards = cards.filter(function (card) { return card.dataset.category === group.id; });
      const entries = groupCards.map(function (card) { return results[card.dataset.questionId]; }).filter(function (entry) {
        return entry && entry.checked !== false;
      });
      const groupCorrect = entries.filter(function (entry) { return entry.correct; }).length;
      const percent = entries.length ? Math.round(groupCorrect / entries.length * 100) : 0;
      const score = make("div", "objective-score" + (entries.length === groupCards.length && percent >= 80 ? " is-mastered" : ""));
      score.appendChild(make("strong", "", group.title));
      score.appendChild(make("span", "", groupCorrect + " / " + entries.length + " correct · " + percent + "%"));
      score.appendChild(make("span", "", entries.length === groupCards.length && percent >= 80 ? "Mastered" : "Target: all attempted and ≥80%"));
      if (assessmentMode === "post-test" && Object.keys(pretestResults).length) {
        const preEntries = groupCards.map(function (card) { return pretestResults[card.dataset.questionId]; }).filter(function (entry) {
          return entry && entry.checked !== false;
        });
        const prePercent = preEntries.length ? Math.round(preEntries.filter(function (entry) { return entry.correct; }).length / preEntries.length * 100) : 0;
        score.appendChild(make("span", "", "Change from pre-test: " + (percent - prePercent >= 0 ? "+" : "") + (percent - prePercent) + " points"));
      }
      objectiveScores.appendChild(score);
    });
  }

  function filterQuestions() {
    const query = search.value.trim().toLowerCase();
    const selectedCategory = category.value;

    document.querySelectorAll(".question-card").forEach(function (card) {
      const matchesText = !query || card.dataset.search.includes(query);
      const matchesCategory = selectedCategory === "all" || card.dataset.category === selectedCategory;
      card.classList.toggle("hidden", !(matchesText && matchesCategory));
    });

    document.querySelectorAll(".quiz-group").forEach(function (group) {
      const hasVisible = Array.from(group.querySelectorAll(".question-card")).some(function (card) {
        return !card.classList.contains("hidden");
      });
      group.classList.toggle("hidden", !hasVisible);
    });

    updateStats();
  }

  document.getElementById("expand-visible").addEventListener("click", function () {
    document.querySelectorAll(".question-card:not(.hidden)").forEach(function (card) { card.open = true; });
  });

  document.getElementById("collapse-all").addEventListener("click", function () {
    document.querySelectorAll(".question-card").forEach(function (card) { card.open = false; });
  });

  function startAssessment(mode) {
    if (Object.keys(results).length) {
      try {
        const history = readHistory();
        history[assessmentMode] = { savedAt: Date.now(), results: results };
        localStorage.setItem(historyKey, JSON.stringify(history));
      } catch (_error) { /* assessment remains usable without history */ }
    }
    assessmentMode = mode;
    try { localStorage.setItem(modeKey, mode); } catch (_error) { /* ignore */ }
    results = {};
    saveResults();
    document.querySelectorAll(".question-card").forEach(function (card) {
      card.querySelectorAll('input[type="radio"]').forEach(function (radio) { radio.checked = false; });
      clearVisualResult(card);
      card.open = false;
    });
    category.value = "all";
    search.value = "";
    filterQuestions();
  }

  document.getElementById("start-pretest").addEventListener("click", function () { startAssessment("pre-test"); });
  document.getElementById("start-posttest").addEventListener("click", function () { startAssessment("post-test"); });
  document.getElementById("retry-weak").addEventListener("click", function () {
    const weak = new Set(groups.filter(function (group) {
      const groupResults = group.questions.map(function (_q, index) { return results[questionId(group, index)]; }).filter(Boolean);
      const checkedResults = groupResults.filter(function (result) { return result.checked !== false; });
      return checkedResults.length < group.questions.length || checkedResults.filter(function (r) { return r.correct; }).length / checkedResults.length < 0.8;
    }).map(function (group) { return group.id; }));
    document.querySelectorAll(".question-card").forEach(function (card) {
      const result = results[card.dataset.questionId];
      card.classList.toggle("hidden", !weak.has(card.dataset.category) || Boolean(result && result.checked !== false && result.correct));
    });
    document.querySelectorAll(".quiz-group").forEach(function (group) { group.classList.toggle("hidden", !group.querySelector(".question-card:not(.hidden)")); });
    updateStats();
  });
  document.getElementById("review-due").addEventListener("click", function () {
    const now = Date.now();
    document.querySelectorAll(".question-card").forEach(function (card) {
      const result = results[card.dataset.questionId];
      card.classList.toggle("hidden", !result || !result.nextReview || result.nextReview > now);
    });
    document.querySelectorAll(".quiz-group").forEach(function (group) { group.classList.toggle("hidden", !group.querySelector(".question-card:not(.hidden)")); });
    updateStats();
  });

  document.getElementById("reset-answers").addEventListener("click", function () {
    results = {};
    saveResults();
    document.querySelectorAll(".question-card").forEach(function (card) {
      card.querySelectorAll("input[type=radio]").forEach(function (radio) { radio.checked = false; });
      clearVisualResult(card);
    });
    category.value = "all";
    search.value = "";
    filterQuestions();
  });

  render();
  const requestedObjective = new URLSearchParams(window.location.search).get("objective");
  if (requestedObjective && groups.some(function (group) { return group.id === requestedObjective; })) category.value = requestedObjective;
  search.addEventListener("input", filterQuestions);
  category.addEventListener("change", filterQuestions);
  filterQuestions();
}());
