(function () {
  "use strict";

  const chapters = [
    {
      title: "Start here",
      items: [
        ["01", "Learning dashboard", "robotics-simulation-engineer/dashboard.html"],
        ["02", "Entry diagnostic", "robotics-simulation-engineer/diagnostic.html"]
      ]
    },
    {
      title: "Robotics simulation",
      items: [
        ["03", "Course and modules", "robotics-simulation-engineer/index.html"],
        ["04", "Architecture and debugging", "robotics-simulation-engineer/architecture.html"],
        ["05", "Reasoning and code flow", "robotics-simulation-engineer/reasoning.html"],
        ["06", "Deep resource route", "robotics-simulation-engineer/resources.html"],
        ["07", "Assessment and mastery", "robotics-simulation-engineer/practice.html"],
        ["08", "External course catalog", "robotics-simulation-engineer/course-catalog.html"],
        ["09", "Executable labs", "labs/index.html"]
      ]
    },
    {
      title: "NPU engineering",
      items: [
        ["10", "Three-course map", "npu-courses/index.html"],
        ["11", "Architecture and memory", "npu-courses/architecture.html"],
        ["12", "Compiler IR and lowering", "npu-courses/compiler.html"],
        ["13", "Quantization and runtime", "npu-courses/deployment.html"],
        ["14", "NPU reference and practice", "npu-practice.html"]
      ]
    },
    {
      title: "Core systems practice",
      items: [
        ["15", "Practice library", "interview-practice.html"],
        ["16", "Deep learning", "deep-learning-practice.html"],
        ["17", "Operating systems", "os-practice.html"],
        ["18", "Embedded systems", "embedded-practice.html"]
      ]
    }
  ];

  function rootPrefix() {
    const path = window.location.pathname.replace(/\\/g, "/");
    return /\/(robotics-simulation-engineer|npu-courses|labs)\//.test(path) ? "../" : "";
  }

  function normalizedPath(value) {
    const url = new URL(value, window.location.href);
    let path = url.pathname.replace(/\/+/g, "/");
    if (path.endsWith("/")) path += "index.html";
    return path.toLowerCase();
  }

  function slug(text, index) {
    const base = text
      .toLowerCase()
      .replace(/&/g, " and ")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
    return base || `section-${index + 1}`;
  }

  function uniqueId(base) {
    let candidate = base;
    let suffix = 2;
    while (document.getElementById(candidate)) {
      candidate = `${base}-${suffix}`;
      suffix += 1;
    }
    return candidate;
  }

  const currentPath = normalizedPath(window.location.href);
  const prefix = rootPrefix();
  const pageTitle = (document.querySelector("h1") || document.querySelector("title"));
  const readableTitle = pageTitle ? pageTitle.textContent.trim() : "Learning page";
  let currentChapter = "Learning library";

  document.body.classList.add("book-layout");

  const progress = document.createElement("div");
  progress.className = "book-progress";
  progress.setAttribute("aria-hidden", "true");
  document.body.prepend(progress);

  const menuButton = document.createElement("button");
  menuButton.className = "book-menu-button";
  menuButton.type = "button";
  menuButton.setAttribute("aria-controls", "book-sidebar");
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.textContent = "☰ Contents";
  document.body.prepend(menuButton);

  const scrim = document.createElement("button");
  scrim.className = "book-scrim";
  scrim.type = "button";
  scrim.setAttribute("aria-label", "Close table of contents");
  document.body.prepend(scrim);

  const sidebar = document.createElement("aside");
  sidebar.id = "book-sidebar";
  sidebar.className = "book-sidebar";
  sidebar.setAttribute("aria-label", "Book chapters and page contents");

  const top = document.createElement("div");
  top.className = "book-sidebar__top";
  top.innerHTML = `
    <button class="book-sidebar__close" type="button" aria-label="Close table of contents">×</button>
    <p class="book-sidebar__eyebrow">Engineering learning book</p>
    <a class="book-sidebar__title" href="${prefix}index.html">Model · Validate · Deploy</a>
    <p class="book-sidebar__location"></p>
  `;
  sidebar.appendChild(top);

  const nav = document.createElement("nav");
  nav.className = "book-sidebar__nav";
  nav.setAttribute("aria-label", "Learning chapters");

  let activeListItem = null;
  chapters.forEach((chapter) => {
    const section = document.createElement("section");
    section.className = "book-chapter";
    const heading = document.createElement("h2");
    heading.className = "book-chapter__title";
    heading.textContent = chapter.title;
    section.appendChild(heading);

    const list = document.createElement("ol");
    list.className = "book-chapter__list";
    chapter.items.forEach(([number, title, path]) => {
      const item = document.createElement("li");
      const anchor = document.createElement("a");
      anchor.className = "book-chapter__link";
      anchor.href = prefix + path;
      anchor.innerHTML = `<span class="book-chapter__number">${number}</span><span>${title}</span>`;
      if (normalizedPath(anchor.href) === currentPath) {
        anchor.setAttribute("aria-current", "page");
        activeListItem = item;
        currentChapter = chapter.title;
      }
      item.appendChild(anchor);
      list.appendChild(item);
    });
    section.appendChild(list);
    nav.appendChild(section);
  });

  const headings = Array.from(document.querySelectorAll("main h2")).filter(
    (heading) => !heading.closest("[hidden]")
  );
  const tocLinks = [];
  if (activeListItem && headings.length) {
    const toc = document.createElement("ol");
    toc.className = "book-page-toc";
    toc.setAttribute("aria-label", "On this page");
    headings.forEach((heading, index) => {
      if (!heading.id) heading.id = uniqueId(slug(heading.textContent.trim(), index));
      const item = document.createElement("li");
      const anchor = document.createElement("a");
      anchor.href = `#${heading.id}`;
      anchor.textContent = heading.textContent.trim();
      anchor.dataset.target = heading.id;
      item.appendChild(anchor);
      toc.appendChild(item);
      tocLinks.push(anchor);
    });
    activeListItem.appendChild(toc);
  }

  sidebar.appendChild(nav);
  document.body.prepend(sidebar);
  top.querySelector(".book-sidebar__location").textContent =
    `${currentChapter} / ${readableTitle}`;

  function setMenu(open) {
    document.body.classList.toggle("book-menu-open", open);
    menuButton.setAttribute("aria-expanded", String(open));
    if (open) sidebar.querySelector(".book-sidebar__close").focus();
    else menuButton.focus();
  }

  menuButton.addEventListener("click", () => setMenu(true));
  scrim.addEventListener("click", () => setMenu(false));
  sidebar.querySelector(".book-sidebar__close").addEventListener("click", () => setMenu(false));
  sidebar.addEventListener("click", (event) => {
    if (event.target.closest("a") && window.matchMedia("(max-width: 900px)").matches) {
      document.body.classList.remove("book-menu-open");
      menuButton.setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.body.classList.contains("book-menu-open")) {
      setMenu(false);
    }
  });

  function updateProgress() {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = scrollable > 0 ? Math.min(1, Math.max(0, window.scrollY / scrollable)) : 0;
    progress.style.width = `${ratio * 100}%`;
  }
  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateProgress);
  updateProgress();

  if (headings.length && "IntersectionObserver" in window) {
    const visible = new Map();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => visible.set(entry.target.id, entry.isIntersecting));
      const current = headings.find((heading) => visible.get(heading.id)) ||
        headings.slice().reverse().find((heading) => heading.getBoundingClientRect().top < 180);
      if (!current) return;
      tocLinks.forEach((link) => {
        const isCurrent = link.dataset.target === current.id;
        link.classList.toggle("is-reading", isCurrent);
        if (isCurrent) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }, { rootMargin: "-12% 0px -72% 0px" });
    headings.forEach((heading) => observer.observe(heading));
  }
}());
