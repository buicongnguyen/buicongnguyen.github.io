(function () {
  "use strict";

  // The book spine: reading order is the array order, and chapter numbers are derived
  // from it, so inserting a page never needs manual renumbering. Every page that loads
  // this script must appear here (scripts/check_site.py enforces it).
  const chapters = [
    {
      title: "Start here",
      items: [
        ["Learning dashboard", "robotics-simulation-engineer/dashboard.html"],
        ["Entry diagnostic", "robotics-simulation-engineer/diagnostic.html"]
      ]
    },
    {
      title: "Robotics simulation",
      items: [
        ["Course and modules", "robotics-simulation-engineer/index.html"],
        ["Architecture and debugging", "robotics-simulation-engineer/architecture.html"],
        ["Reasoning and code flow", "robotics-simulation-engineer/reasoning.html"],
        ["ROS 2 dual-mode setup", "robotics-simulation-engineer/ros2-dual-mode.html"]
      ]
    },
    {
      title: "Isaac Sim practical labs",
      items: [
        ["Ten-lab path and shared startup", "robotics-simulation-engineer/ros2-labs.html"],
        ["Lab 01 · Simulation clock", "robotics-simulation-engineer/isaac-sim-gui-clock-test.html"],
        ["Lab 02 · Joint states and TF", "robotics-simulation-engineer/lab-02-joint-states-tf.html"],
        ["Lab 03 · Command watchdog", "robotics-simulation-engineer/lab-03-cmd-vel-watchdog.html"],
        ["Lab 04 · Camera contracts", "robotics-simulation-engineer/lab-04-camera-depth.html"],
        ["Lab 05 · Record and replay", "robotics-simulation-engineer/lab-05-rosbag-validation.html"],
        ["Lab 06 · Model audit", "robotics-simulation-engineer/lab-06-urdf-model-audit.html"],
        ["Lab 07 · Physics identification", "robotics-simulation-engineer/lab-07-physics-identification.html"],
        ["Lab 08 · Regression CI", "robotics-simulation-engineer/lab-08-regression-ci.html"],
        ["Lab 09 · Performance profiling", "robotics-simulation-engineer/lab-09-performance-profiling.html"],
        ["Lab 10 · Robustness", "robotics-simulation-engineer/lab-10-domain-randomization.html"]
      ]
    },
    {
      title: "Practice and reference",
      items: [
        ["Executable coding labs", "labs/index.html"],
        ["Assessment and mastery", "robotics-simulation-engineer/practice.html"],
        ["Deep resource route", "robotics-simulation-engineer/resources.html"],
        ["External course catalog", "robotics-simulation-engineer/course-catalog.html"]
      ]
    },
    {
      title: "NPU engineering",
      items: [
        ["Three-course map", "npu-courses/index.html"],
        ["Architecture and memory", "npu-courses/architecture.html"],
        ["Compiler IR and lowering", "npu-courses/compiler.html"],
        ["Quantization and runtime", "npu-courses/deployment.html"],
        ["NPU reference and practice", "npu-practice.html"]
      ]
    },
    {
      title: "Core systems practice",
      items: [
        ["Practice library", "interview-practice.html"],
        ["Deep learning", "deep-learning-practice.html"],
        ["Operating systems", "os-practice.html"],
        ["Embedded systems", "embedded-practice.html"]
      ]
    }
  ];
  const chapterItems = chapters.flatMap((chapter) =>
    chapter.items.map((item) => ({ title: item[0], path: item[1], chapter: chapter.title }))
  );
  chapterItems.forEach((item, index) => { item.number = String(index + 1).padStart(2, "0"); });
  const numberByPath = new Map(chapterItems.map((item) => [item.path, item.number]));

  // This script lives at the site root, so its own URL locates every chapter at any depth
  // (GitHub Pages or a local file:// checkout) without a list of known folders.
  const scriptUrl = document.currentScript ? document.currentScript.src : window.location.href;
  const siteRoot = new URL(".", scriptUrl);

  function rootPrefix() {
    return siteRoot.href;
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
  const currentItemIndex = chapterItems.findIndex(
    (item) => normalizedPath(prefix + item.path) === currentPath
  );
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
    <a class="book-sidebar__title" href="${prefix}robotics-simulation-engineer/dashboard.html">Model · Validate · Deploy</a>
    <p class="book-sidebar__location"></p>
    <a class="book-sidebar__portfolio" href="${prefix}index.html">Portfolio home</a>
  `;
  sidebar.appendChild(top);

  const searchWrap = document.createElement("div");
  searchWrap.className = "book-search";
  searchWrap.innerHTML = `
    <label for="book-search-input">Find a chapter</label>
    <input id="book-search-input" type="search" placeholder="Search ${chapterItems.length} chapters" autocomplete="off">
    <p class="book-search__status" aria-live="polite"></p>
  `;
  sidebar.appendChild(searchWrap);

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
    chapter.items.forEach(([title, path]) => {
      const number = numberByPath.get(path);
      const item = document.createElement("li");
      item.dataset.bookSearch = `${number} ${title} ${chapter.title}`.toLowerCase();
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
  top.querySelector(".book-sidebar__location").textContent =
    `${currentChapter} / ${readableTitle}`;

  const skipLink = document.querySelector(".skip-link");
  if (skipLink) {
    skipLink.after(menuButton, scrim, sidebar);
  } else {
    document.body.prepend(sidebar);
    document.body.prepend(scrim);
    document.body.prepend(menuButton);
  }

  const search = searchWrap.querySelector("input");
  const searchStatus = searchWrap.querySelector(".book-search__status");

  function filterChapters() {
    const query = search.value.trim().toLowerCase();
    let matches = 0;
    nav.querySelectorAll(".book-chapter").forEach((chapter) => {
      const items = Array.from(chapter.querySelector(".book-chapter__list").children);
      items.forEach((item) => {
        const match = !query || item.dataset.bookSearch.includes(query);
        item.hidden = !match;
        if (match) matches += 1;
      });
      chapter.hidden = !items.some((item) => !item.hidden);
    });
    searchStatus.textContent = query
      ? `${matches} chapter${matches === 1 ? "" : "s"} found`
      : "";
  }

  search.addEventListener("input", filterChapters);
  search.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && search.value) {
      search.value = "";
      filterChapters();
      event.stopPropagation();
    }
  });

  if (activeListItem) {
    requestAnimationFrame(() => {
      const activeLink = activeListItem.querySelector(".book-chapter__link");
      const topBoundary = top.getBoundingClientRect().bottom + searchWrap.getBoundingClientRect().height;
      const activeRect = activeLink.getBoundingClientRect();
      if (activeRect.top < topBoundary || activeRect.bottom > sidebar.clientHeight) {
        sidebar.scrollTop = Math.max(0, activeLink.offsetTop - sidebar.clientHeight / 2);
      }
    });
  }

  const mobileQuery = window.matchMedia("(max-width: 900px)");

  function syncSidebarAccessibility() {
    const hiddenOnMobile = mobileQuery.matches &&
      !document.body.classList.contains("book-menu-open");
    sidebar.toggleAttribute("inert", hiddenOnMobile);
    sidebar.setAttribute("aria-hidden", String(hiddenOnMobile));
  }

  function setMenu(open, restoreFocus = true) {
    document.body.classList.toggle("book-menu-open", open);
    menuButton.setAttribute("aria-expanded", String(open));
    syncSidebarAccessibility();
    if (open) sidebar.querySelector(".book-sidebar__close").focus();
    else if (restoreFocus) menuButton.focus();
  }

  menuButton.addEventListener("click", () => setMenu(true));
  scrim.addEventListener("click", () => setMenu(false));
  sidebar.querySelector(".book-sidebar__close").addEventListener("click", () => setMenu(false));
  sidebar.addEventListener("click", (event) => {
    if (event.target.closest("a") && mobileQuery.matches) {
      setMenu(false, false);
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.body.classList.contains("book-menu-open")) {
      setMenu(false);
    }
  });
  mobileQuery.addEventListener("change", () => {
    document.body.classList.remove("book-menu-open");
    menuButton.setAttribute("aria-expanded", "false");
    syncSidebarAccessibility();
  });
  syncSidebarAccessibility();

  const main = document.querySelector("main");
  if (main && currentItemIndex >= 0) {
    const pagination = document.createElement("nav");
    pagination.className = "book-pagination";
    pagination.setAttribute("aria-label", "Previous and next chapters");

    const previous = chapterItems[currentItemIndex - 1];
    const next = chapterItems[currentItemIndex + 1];

    function paginationLink(item, direction) {
      if (!item) {
        const spacer = document.createElement("span");
        spacer.className = "book-pagination__spacer";
        spacer.setAttribute("aria-hidden", "true");
        return spacer;
      }
      const anchor = document.createElement("a");
      anchor.className = `book-pagination__link book-pagination__link--${direction}`;
      anchor.href = prefix + item.path;
      anchor.innerHTML = `
        <span>${direction === "previous" ? "← Previous" : "Next →"}</span>
        <strong>${item.number} · ${item.title}</strong>
        <small>${item.chapter}</small>
      `;
      return anchor;
    }

    pagination.appendChild(paginationLink(previous, "previous"));
    pagination.appendChild(paginationLink(next, "next"));
    main.appendChild(pagination);
  }

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
