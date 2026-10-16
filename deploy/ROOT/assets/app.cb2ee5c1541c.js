/* Progressive enhancements only. The complete portfolio is readable without JS. */
(() => {
  "use strict";

  const doc = document;
  const root = doc.documentElement;
  const chinese = String(doc.body.dataset.lang || root.lang || "en").toLowerCase().startsWith("zh");
  root.classList.add("js");

  // A failed optional feature must not disable navigation or another feature.
  function run(name, initialise) {
    try {
      initialise();
    } catch (error) {
      if (window.console && typeof window.console.warn === "function") {
        window.console.warn(`[Portfolio] ${name} enhancement unavailable.`, error);
      }
    }
  }

  function focusElement(element) {
    if (!element || typeof element.focus !== "function" || !element.isConnected) return;
    try { element.focus({ preventScroll: true }); }
    catch (_) { element.focus(); }
  }

  function liveRegion(element) {
    if (!element) return;
    element.setAttribute("role", "status");
    element.setAttribute("aria-live", "polite");
    element.setAttribute("aria-atomic", "true");
  }

  function describeWith(control, id) {
    if (!control || !id) return;
    const ids = (control.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
    if (!ids.includes(id)) ids.push(id);
    control.setAttribute("aria-describedby", ids.join(" "));
  }

  function normalise(value) {
    let text = String(value || "");
    if (typeof text.normalize === "function") text = text.normalize("NFKD");
    return text
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/&/g, " and ")
      .replace(/[^a-z0-9\u3400-\u9fff]+/g, " ")
      .trim()
      .replace(/\s+/g, " ");
  }

  // Equivalents are indexed in both directions; short aliases have word boundaries.
  // For example, searching AI must not match an unrelated word such as "detail".
  const aliasGroups = [
    ["ai", "artificial intelligence", "adaptive intelligence", "人工智能"],
    ["ml", "machine learning", "机器学习"],
    ["nlp", "natural language processing", "natural language", "language technology", "text processing", "自然语言处理", "自然语言", "语言技术", "文本处理"],
    ["gpu", "gpus", "graphics processing unit", "graphics processing units", "graphical processing units", "gpu computing", "cuda", "图形处理器", "图形处理单元", "显卡计算", "gpu计算"],
    ["dl", "deep learning", "深度学习"]
  ].map(group => group.map(normalise));
  const aliasLookup = new Map();
  aliasGroups.forEach((group, index) => group.forEach(term => aliasLookup.set(term, index)));

  function containsTerm(text, term) {
    if (!/[a-z0-9]/.test(term)) return text.includes(term);
    // Every term is normalised to letters, numbers, Chinese characters and spaces.
    return new RegExp(`(?:^|[^a-z0-9])${term}(?=$|[^a-z0-9])`).test(text);
  }

  function searchIndex(value) {
    const text = normalise(value);
    const aliases = new Set();
    const expansions = [];
    aliasGroups.forEach((group, index) => {
      if (group.some(term => containsTerm(text, term))) {
        aliases.add(index);
        expansions.push(...group);
      }
    });
    return { text: `${text} ${expansions.join(" ")}`, aliases };
  }

  function matchesSearch(index, query) {
    const phrase = normalise(query);
    if (!phrase) return true;
    if (aliasLookup.has(phrase)) return index.aliases.has(aliasLookup.get(phrase));
    return phrase.split(" ").every(term => {
      if (aliasLookup.has(term)) return index.aliases.has(aliasLookup.get(term));
      return index.text.includes(term);
    });
  }

  run("Theme", () => {
    const buttons = Array.from(doc.querySelectorAll("[data-theme-toggle]"));
    const key = "portfolio-theme"; // Retain preferences saved by the previous site.
    let preference = null;
    try {
      const saved = window.localStorage.getItem(key);
      if (saved === "light" || saved === "dark") preference = saved;
    } catch (_) { /* Storage can be unavailable in a private or restricted context. */ }

    const media = typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-color-scheme: dark)") : null;

    function applyTheme() {
      const theme = preference || (media && media.matches ? "dark" : "light");
      root.dataset.theme = theme;
      const nextLabel = chinese
        ? (theme === "dark" ? "切换为浅色模式" : "切换为深色模式")
        : (theme === "dark" ? "Use light theme" : "Use dark theme");
      buttons.forEach(button => {
        button.setAttribute("aria-label", nextLabel);
        button.setAttribute("title", nextLabel);
        button.dataset.themeState = theme;
        const label = button.querySelector("[data-theme-label]");
        if (label) label.textContent = nextLabel;
      });
    }

    buttons.forEach(button => button.addEventListener("click", () => {
      preference = root.dataset.theme === "dark" ? "light" : "dark";
      applyTheme();
      try { window.localStorage.setItem(key, preference); }
      catch (_) { /* The selected theme still works for this page. */ }
    }));

    if (media) {
      const onSystemChange = () => { if (!preference) applyTheme(); };
      if (typeof media.addEventListener === "function") media.addEventListener("change", onSystemChange);
      else if (typeof media.addListener === "function") media.addListener(onSystemChange);
    }
    window.addEventListener("storage", event => {
      if (event.key !== key && event.key !== null) return;
      preference = event.newValue === "light" || event.newValue === "dark" ? event.newValue : null;
      applyTheme();
    });
    applyTheme();
    root.classList.add("theme-ready");
  });

  run("Mobile navigation", () => {
    const button = doc.querySelector("[data-menu-button]");
    if (!button) return;
    const controlledId = button.getAttribute("aria-controls");
    const nav = (controlledId ? doc.getElementById(controlledId) : null) || doc.querySelector("[data-nav-links]");
    if (!nav) return;
    if (!nav.id) nav.id = "primary-nav";
    button.setAttribute("aria-controls", nav.id);
    const media = typeof window.matchMedia === "function" ? window.matchMedia("(max-width: 1050px)") : null;
    let expanded = false;
    const isMobile = () => media ? media.matches : window.innerWidth <= 1050;

    function render() {
      const mobile = isMobile();
      if (!mobile) expanded = false;
      nav.classList.toggle("is-open", expanded && mobile);
      button.setAttribute("aria-expanded", String(!mobile || expanded));
      button.setAttribute("aria-label", chinese
        ? (expanded ? "关闭导航菜单" : "打开导航菜单")
        : (expanded ? "Close navigation menu" : "Open navigation menu"));
    }

    function close(restoreFocus) {
      expanded = false;
      render();
      if (restoreFocus) focusElement(button);
    }

    button.addEventListener("click", () => { expanded = !expanded; render(); });
    nav.addEventListener("click", event => {
      if (event.target instanceof Element && event.target.closest("a")) close(false);
    });
    doc.addEventListener("click", event => {
      if (expanded && !nav.contains(event.target) && !button.contains(event.target)) close(false);
    });
    doc.addEventListener("keydown", event => {
      if (!event.defaultPrevented && event.key === "Escape" && expanded && isMobile() && !doc.querySelector("dialog[open]")) {
        event.preventDefault();
        close(true);
      }
    });
    if (media && typeof media.addEventListener === "function") media.addEventListener("change", render);
    else if (media && typeof media.addListener === "function") media.addListener(render);
    else window.addEventListener("resize", render, { passive: true });

    render();
    root.classList.add("menu-ready");
  });

  run("Catalogue filters", () => {
    const allowedKeys = new Set(["programme", "level", "area", "category", "status"]);
    const isAll = value => !value || String(value).toLowerCase() === "all";
    const groups = Array.from(doc.querySelectorAll("[data-filter-group]"));

    groups.forEach((group, groupIndex) => run(`Filter group ${groupIndex + 1}`, () => {
      const query = group.querySelector("[data-filter-query]");
      const selects = Array.from(group.querySelectorAll("[data-filter-select]"))
        .filter(select => allowedKeys.has(select.name));
      const items = Array.from(group.querySelectorAll("[data-filter-item]"));
      const count = group.querySelector("[data-filter-count]");
      const empty = group.querySelector("[data-filter-empty]");
      const reset = group.querySelector("[data-filter-reset]");
      if (!items.length || (!query && !selects.length)) return;

      const indices = new Map(items.map(item => [item, searchIndex([
        item.dataset.search,
        item.textContent,
        ...Array.from(allowedKeys, key => item.getAttribute(`data-${key}`) || "")
      ].join(" "))]));
      const defaults = new Map(selects.map(select => {
        const all = Array.from(select.options).find(option => isAll(option.value));
        return [select, all ? all.value : (select.options[0] ? select.options[0].value : "")];
      }));
      if (count) {
        liveRegion(count);
        if (!count.id) count.id = `filter-count-${groupIndex + 1}`;
        [query, ...selects].forEach(control => describeWith(control, count.id));
      }

      function readURL() {
        if (query) query.value = "";
        selects.forEach(select => { select.value = defaults.get(select); });
        try {
          const params = new URLSearchParams(window.location.search);
          if (query && params.has("q")) query.value = params.get("q") || "";
          selects.forEach(select => {
            const value = params.get(select.name);
            if (value !== null && Array.from(select.options).some(option => option.value === value)) {
              select.value = value;
            }
          });
        } catch (_) { /* All records remain available if URL APIs are restricted. */ }
      }

      function writeURL() {
        try {
          const url = new URL(window.location.href);
          if (query) {
            if (query.value.trim()) url.searchParams.set("q", query.value.trim());
            else url.searchParams.delete("q");
          }
          selects.forEach(select => {
            if (!isAll(select.value)) url.searchParams.set(select.name, select.value);
            else url.searchParams.delete(select.name);
          });
          // Retain unrelated query parameters, the current fragment, and history state.
          if (url.href !== window.location.href) window.history.replaceState(window.history.state, "", url.href);
        } catch (_) { /* Filtering works on file:// and when history writes are denied. */ }
      }

      function matchesSelection(item, select) {
        if (isAll(select.value)) return true;
        const actual = (item.getAttribute(`data-${select.name}`) || "").trim().toLowerCase();
        const wanted = select.value.trim().toLowerCase();
        return actual === wanted || actual.split(/[\s,|]+/).includes(wanted);
      }

      function render(updateURL) {
        let visible = 0;
        items.forEach(item => {
          const show = matchesSearch(indices.get(item), query ? query.value : "")
            && selects.every(select => matchesSelection(item, select));
          item.hidden = !show;
          if (show) visible += 1;
        });
        if (count) {
          const template = count.dataset.countTemplate || (chinese ? "显示 {count} / {total} 项" : "Showing {count} of {total} results.");
          count.textContent = template
            .replace(/\{(?:count|visible)\}/g, String(visible))
            .replace(/\{total\}/g, String(items.length));
        }
        if (empty) empty.hidden = visible !== 0;
        const active = Boolean(query && query.value.trim()) || selects.some(select => !isAll(select.value));
        if (reset) reset.disabled = !active;
        group.classList.toggle("has-active-filters", active);
        if (updateURL) writeURL();
      }

      if (query) {
        query.addEventListener("input", () => render(true));
        query.addEventListener("keydown", event => {
          if (event.key === "Escape" && query.value) {
            event.preventDefault();
            query.value = "";
            render(true);
          }
        });
      }
      selects.forEach(select => select.addEventListener("change", () => render(true)));
      if (reset) reset.addEventListener("click", event => {
        event.preventDefault();
        if (query) query.value = "";
        selects.forEach(select => { select.value = defaults.get(select); });
        render(true);
        focusElement(query || selects[0]);
      });
      group.addEventListener("submit", event => {
        if (event.target instanceof HTMLFormElement) {
          event.preventDefault();
          render(true);
        }
      });
      window.addEventListener("popstate", () => { readURL(); render(false); });
      readURL();
      render(false);
      group.classList.add("filter-ready");
    }));
  });

  run("Quick navigation", () => {
    const dialog = doc.querySelector("[data-command-dialog]");
    const openButtons = Array.from(doc.querySelectorAll("[data-command-open]"));
    if (!dialog || typeof dialog.showModal !== "function" || typeof dialog.close !== "function") return;
    const input = dialog.querySelector("[data-command-input]");
    const list = dialog.querySelector("[data-command-list]");
    const closeButton = dialog.querySelector("[data-command-close]");
    if (!input || !list || !closeButton) return;
    const entries = Array.from(list.querySelectorAll("[data-search-entry]"));
    const indices = new Map(entries.map(entry => [entry, searchIndex(`${entry.dataset.search || ""} ${entry.textContent}`)]));
    const empty = dialog.querySelector("[data-command-empty]");
    const status = dialog.querySelector("[data-command-status]");
    let previousFocus = null;
    liveRegion(status);

    function visibleLinks() {
      return entries.filter(entry => !entry.hidden).map(entry => entry.querySelector("a[href]")).filter(Boolean);
    }

    function filter() {
      let visible = 0;
      entries.forEach(entry => {
        const show = matchesSearch(indices.get(entry), input.value);
        entry.hidden = !show;
        if (show) visible += 1;
      });
      if (empty) empty.hidden = visible !== 0;
      if (status) status.textContent = chinese ? `找到 ${visible} 个页面` : `${visible} ${visible === 1 ? "page" : "pages"} found.`;
    }

    function close() { if (dialog.open) dialog.close(); }
    function open(opener) {
      if (dialog.open) return true;
      previousFocus = opener || doc.activeElement;
      input.value = "";
      filter();
      try {
        dialog.showModal();
        focusElement(input);
        return true;
      } catch (_) {
        root.classList.remove("command-ready");
        return false;
      }
    }

    openButtons.forEach(button => button.addEventListener("click", () => open(button)));
    closeButton.addEventListener("click", event => { event.preventDefault(); close(); });
    dialog.addEventListener("close", () => {
      focusElement(previousFocus && previousFocus.isConnected ? previousFocus : openButtons[0]);
    });
    dialog.addEventListener("cancel", event => { event.preventDefault(); close(); });
    dialog.addEventListener("click", event => {
      if (event.target !== dialog || event.detail === 0) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close();
    });
    dialog.addEventListener("submit", event => { event.preventDefault(); });
    input.addEventListener("input", filter);
    input.addEventListener("keydown", event => {
      const links = visibleLinks();
      if (event.key === "ArrowDown" && links.length) {
        event.preventDefault();
        focusElement(links[0]);
      } else if (event.key === "Enter") {
        event.preventDefault();
        if (links.length) links[0].click();
      }
    });
    list.addEventListener("keydown", event => {
      if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
      const links = visibleLinks();
      const current = links.indexOf(doc.activeElement);
      if (current < 0 || !links.length) return;
      event.preventDefault();
      if (event.key === "Home") focusElement(links[0]);
      else if (event.key === "End") focusElement(links[links.length - 1]);
      else if (event.key === "ArrowUp") focusElement(current ? links[current - 1] : input);
      else focusElement(links[Math.min(current + 1, links.length - 1)]);
    });
    list.addEventListener("click", event => {
      if (event.target instanceof Element && event.target.closest("a[href]")) close();
    });
    doc.addEventListener("keydown", event => {
      if (event.isComposing || event.altKey || !(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "k") return;
      if (event.target instanceof Element && event.target.closest('[contenteditable="true"]')) return;
      if (dialog.open) { event.preventDefault(); close(); }
      else if (open(doc.activeElement)) event.preventDefault();
    });
    filter();
    root.classList.add("command-ready");
  });

  run("Copy email", () => {
    const buttons = Array.from(doc.querySelectorAll("[data-copy]"));
    buttons.forEach((button, index) => {
      const value = button.getAttribute("data-copy") || "";
      if (!value) return;
      const copyGroup = button.closest("[data-copy-group]");
      let status = (copyGroup ? copyGroup.querySelector("[data-copy-status]") : null)
        || doc.querySelector("[data-copy-status]");
      if (!status) {
        status = doc.createElement("span");
        status.className = "copy-status";
        status.setAttribute("data-copy-status", "");
        button.insertAdjacentElement("afterend", status);
      }
      if (!status.id) status.id = `copy-status-${index + 1}`;
      liveRegion(status);
      describeWith(button, status.id);
      const label = button.querySelector("[data-copy-label]") || (button.childElementCount === 0 ? button : null);
      const originalLabel = label ? label.textContent : "";
      let restoreTimer;

      button.addEventListener("click", async event => {
        event.preventDefault();
        window.clearTimeout(restoreTimer);
        if (label) label.textContent = originalLabel;
        const manualMessage = chinese
          ? `此环境无法自动复制，请选择并复制邮箱：${value}`
          : `Automatic copying is unavailable here. Select and copy this email address: ${value}`;
        if (!window.isSecureContext || !navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          status.textContent = manualMessage;
          return;
        }
        button.disabled = true;
        try {
          await navigator.clipboard.writeText(value);
          const message = button.dataset.copied || (chinese ? "邮箱已复制" : "Email copied");
          status.textContent = message;
          if (label) label.textContent = message;
          restoreTimer = window.setTimeout(() => { if (label) label.textContent = originalLabel; }, 2400);
        } catch (_) {
          // Never navigate to mailto: or claim success when clipboard access fails.
          status.textContent = manualMessage;
        } finally {
          button.disabled = false;
        }
      });
    });
    root.classList.add("copy-ready");
  });

  run("Print", () => {
    if (typeof window.print !== "function") return;
    doc.querySelectorAll("[data-print]").forEach(button => button.addEventListener("click", event => {
      event.preventDefault();
      run("Print dialog", () => window.print());
    }));
    root.classList.add("print-ready");
  });
})();
