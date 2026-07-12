(function () {
  "use strict";

  const groups = window.roboticsSimulationQuestionGroups || [];
  const storageKey = "robotics-simulation-engineer-practice-v1";
  const root = document.getElementById("questions-root");
  const search = document.getElementById("question-search");
  const category = document.getElementById("question-category");
  const stats = document.getElementById("quiz-stats");
  const intros = {
    "models-frames": "Kinematic trees, transform conventions, mass properties, collision geometry, and model conversion.",
    "dynamics-contact-control": "Timestep, constraints, friction, restitution, actuator limits, delay, control, and energy.",
    "simulators-performance": "Benchmark design, headless sensors, batching, reset cost, determinism, and cross-simulator comparison.",
    "ros2-sensors-pipelines": "Clock, TF, QoS, sensor conventions, noise, callback architecture, watchdogs, and replay.",
    "sim-to-real-debugging-ci": "Identification, randomization, artifact exploitation, failure isolation, tolerances, provenance, and CI."
  };

  function readResults() {
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey) || "{}");
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
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

  function applyResult(card, question, selected) {
    clearVisualResult(card);
    const choices = card.querySelectorAll(".choice");
    choices[question.answer].classList.add("is-correct");
    const correct = selected === question.answer;
    if (!correct && choices[selected]) choices[selected].classList.add("is-wrong");

    const feedback = card.querySelector(".feedback");
    feedback.classList.add(correct ? "is-correct" : "is-wrong");
    feedback.textContent = correct
      ? "Correct. " + question.why
      : "Not yet. The correct answer is " + String.fromCharCode(65 + question.answer) + ". " + question.why;
    card.classList.add("is-answered");
    return correct;
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
        if (results[id]) {
          delete results[id];
          saveResults();
          clearVisualResult(card);
          updateStats();
        }
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
      const correct = applyResult(card, question, selectedIndex);
      results[id] = { selected: selectedIndex, correct: correct };
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
      applyResult(card, question, saved.selected);
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
    const resultEntries = Object.entries(results).filter(function (entry) { return validIds.has(entry[0]); });
    const correct = resultEntries.filter(function (entry) { return entry[1].correct; }).length;
    stats.textContent = visible + " of " + cards.length + " questions shown · " + resultEntries.length + " answered · " + correct + " correct";
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

  document.getElementById("reset-answers").addEventListener("click", function () {
    if (!Object.keys(results).length) return;
    results = {};
    saveResults();
    document.querySelectorAll(".question-card").forEach(function (card) {
      card.querySelectorAll("input[type=radio]").forEach(function (radio) { radio.checked = false; });
      clearVisualResult(card);
    });
    updateStats();
  });

  render();
  search.addEventListener("input", filterQuestions);
  category.addEventListener("change", filterQuestions);
  filterQuestions();
}());
