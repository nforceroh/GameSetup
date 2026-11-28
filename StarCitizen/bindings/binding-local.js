(() => {
  const data = window.bindingLocalData || [];
  const liveBuckets = window.bindingLiveBuckets || {};
  let labelMode = "Player";
  let searchQuery = "";
  let zoomScale = 1;
  let legendHidden = false;
  let leftMenuHidden = false;

  // Colorblind-safe (protanopia/deuteranopia) category palette.
  // Optimized for min pairwise CIEDE2000 >= ~15 under both CVD simulations.
  const CVD_COLORS = {
    "Combat": "rgb(255,255,0)",
    "Flight Control": "rgb(74,229,140)",
    "Turret": "rgb(0,109,255)",
    "Power": "rgb(0,255,255)",
    "Mining": "rgb(195,177,245)",
    "Salvage": "rgb(74,120,244)",
    "Camera": "rgb(199,163,229)",
    "Modifier": "rgb(255,255,255)",
    "Miscellaneous": "rgb(113,193,218)",
    "Unbound": "rgb(153,153,153)",
  };
  // Original site colors -> category, for remapping label/swatch colors.
  // Labels use hex inline styles; legend swatches use rgb().
  const ORIG_COLOR_TO_CATEGORY = {
    "#C1272D": "Combat",
    "#FF8089": "Flight Control",
    "#3FA9F5": "Turret",
    "#00FFFF": "Power",
    "#00FF00": "Mining",
    "#00A99D": "Salvage",
    "#F15A24": "Camera",
    "#FFFFFF": "Modifier",
    "#FFB231": "Miscellaneous",
    "#999999": "Unbound",
    "rgb(193, 39, 45)": "Combat",
    "rgb(255, 128, 137)": "Flight Control",
    "rgb(63, 169, 245)": "Turret",
    "rgb(0, 255, 255)": "Power",
    "rgb(0, 255, 0)": "Mining",
    "rgb(0, 169, 157)": "Salvage",
    "rgb(241, 90, 36)": "Camera",
    "rgb(255, 255, 255)": "Modifier",
    "rgb(255, 178, 49)": "Miscellaneous",
    "rgb(153, 153, 153)": "Unbound",
  };

  const normalizeColor = (value) => {
    let v = value.trim().toUpperCase();
    if (v.startsWith("RGB")) {
      const parts = v.match(/\d+/g);
      if (parts && parts.length === 3) {
        v = "#" + parts.map((p) => (+p).toString(16).padStart(2, "0")).join("").toUpperCase();
      }
    }
    return v;
  };

  const applyCvdColors = () => {
    // Recolor dynamic binding labels by their original site color.
    document
      .querySelectorAll(
        '.react-transform-component div[style*="Khand"][style*="cursor: pointer"], .react-transform-component [style*="cursor:pointer"]',
      )
      .forEach((el) => {
        const style = el.getAttribute("style") || "";
        const match = style.match(/color:\s*(#[0-9A-Fa-f]{3,8}|rgb\([^)]+\))/);
        if (!match) return;
        const category = ORIG_COLOR_TO_CATEGORY[normalizeColor(match[1])];
        if (!category) return;
        el.style.color = CVD_COLORS[category];
      });

    // Recolor legend swatches (background or border colored elements).
    document
      .querySelectorAll(".stv-chart span, .stv-chart div")
      .forEach((el) => {
        const bg = el.style.backgroundColor || "";
        const border = el.style.borderColor || "";
        const bgKey = normalizeColor(bg);
        const borderKey = normalizeColor(border);
        const category = ORIG_COLOR_TO_CATEGORY[bgKey] ||
          ORIG_COLOR_TO_CATEGORY[borderKey];
        if (!category) return;
        if (bgKey) el.style.backgroundColor = CVD_COLORS[category];
        if (borderKey) el.style.borderColor = CVD_COLORS[category];
      });
  };

  const clean = (value) =>
    String(value || "")
      .replace(/^(?:\[[^\]]+\]\s*)+/g, "")
      .replace(/[_]/g, " ")
      .replace(/[^a-z0-9]+/gi, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();

  const liveBucketsForText = (text) => {
    const normalized = clean(text);
    const buckets = new Set();
    if (!normalized) return buckets;

    Object.entries(liveBuckets).forEach(([bucket, labels]) => {
      if (labels.some((label) => clean(label) === normalized)) {
        buckets.add(bucket);
      }
    });

    return buckets;
  };

  const findBehavior = (text) => {
    const normalized = clean(text);
    if (!normalized) return null;

    const exact = data.find((row) =>
      [row.labelPlayer, row.labelDisplay, row.labelActionMap].some(
        (value) => clean(value) === normalized,
      )
    );
    if (exact) return exact;

    return data.find((row) =>
      [row.labelPlayer, row.labelDisplay, row.labelActionMap].some((value) => {
        const candidate = clean(value);
        if (!candidate || candidate.length < 4 || normalized.length < 4) {
          return false;
        }
        return (
          normalized.includes(candidate) ||
          candidate.includes(normalized)
        );
      })
    ) || null;
  };

  const formatMarkers = (row) =>
    (row.markers || [])
      .map((marker) => `[${marker}] `)
      .join("");

  const labelForMode = (row) => {
    if (labelMode === "CIG") return row.labelDisplay || row.labelPlayer || "unbound";
    if (labelMode === "Raw") return row.labelActionMap || row.labelPlayer || "unbound";
    return row.labelPlayer || "unbound";
  };

  const getScrollboxes = () =>
    [...document.querySelectorAll(".stv-scrollbox")];

  const getBindingLabels = () => {
    const labels = [
      ...document.querySelectorAll(
        '.react-transform-component div[style*="Khand"][style*="cursor: pointer"]',
      ),
      ...document.querySelectorAll(
        '.react-transform-component [style*="cursor:pointer"]',
      ),
    ].filter((element) => {
      const text = (element.textContent || element.innerText || "").trim();
      if (!text) return false;
      // Marker-prefixed labels contain a bold <span> for the [M]/[H]/[DT]
      // prefix; only reject elements with non-marker child content.
      return [...element.children].every((child) =>
        (child.tagName === "SPAN" &&
          /^(?:\[[A-Z]+\])+$/.test(child.textContent.trim())) ||
        (child.tagName === "BUTTON" &&
          /^[^\w\s]$/.test(child.textContent.trim()))
      );
    });

    return labels.filter((element, index, all) =>
      all.indexOf(element) === index
    );
  };

  const applyLabelMode = () => {
    [...getScrollboxes().flatMap((scrollbox) =>
      [...scrollbox.children]), ...getBindingLabels()].forEach((item) => {
      const original =
        item.dataset.originalText ||
        (item.textContent || item.innerText || "").trim();
      if (!original) return;

      const row = findBehavior(original);
      if (!row) return;

      item.dataset.originalText = original;
      item.textContent =
        `${formatMarkers(row)}${labelForMode(row)}`.trim();
    });
  };

  const enabledCategoryMap = (checkboxes) => {
    const enabledBuckets = new Set();
    const enabledCategories = new Set();

    checkboxes.forEach((checkbox) => {
      if (!checkbox.checked) return;
      const label =
        checkbox.closest("label")?.innerText?.trim() ||
        checkbox.parentElement?.innerText?.trim() ||
        "";

      if (["Combat", "Flight Control", "Turret", "Power", "Mining",
        "Salvage", "Camera", "Modifier", "Miscellaneous", "Unbound"].includes(label)) {
        enabledBuckets.add(label);
      } else if (label === "Ground Vehicles") {
        enabledCategories.add("Vehicle");
      } else if (label === "EVA") {
        enabledCategories.add("E.V.A.");
      } else if (label === "On Foot") {
        enabledCategories.add("ON FOOT");
      }
    });

    return { enabledBuckets, enabledCategories };
  };

  const applyFilters = () => {
    const checkboxes = [...document.querySelectorAll('input[type="checkbox"]')];
    const { enabledBuckets, enabledCategories } =
      enabledCategoryMap(checkboxes);
    const anyEnabled =
      enabledBuckets.size > 0 || enabledCategories.size > 0;

    if (enabledBuckets.size === 0) {
      [...getScrollboxes().flatMap((scrollbox) =>
        [...scrollbox.children]), ...getBindingLabels()].forEach((item) => {
        item.dataset.localHidden = "true";
        item.style.setProperty("display", "none", "important");
      });
      getScrollboxes().forEach((scrollbox) => {
        scrollbox.dataset.localHidden = "true";
        scrollbox.style.setProperty("display", "none", "important");
      });
      return;
    }

    [...getScrollboxes().flatMap((scrollbox) =>
      [...scrollbox.children]), ...getBindingLabels()].forEach((item) => {
      const original =
        item.dataset.originalText ||
        (item.textContent || item.innerText || "").trim();
      if (!original) return;

      const row = findBehavior(original);
      const liveBucketsForItem = liveBucketsForText(original);

      if (liveBucketsForItem.size > 0) {
        const visible = [...liveBucketsForItem].some((bucket) =>
          enabledBuckets.has(bucket)
        );
        item.style.display =
          visible ? "" : "none";
        item.dataset.localHidden = visible ? "false" : "true";
        return;
      }

      if (!row) {
        item.style.display = "none";
        item.dataset.localHidden = "true";
        return;
      }

      item.dataset.originalText = original;
      const matchesSearch =
        !searchQuery ||
        original.toLowerCase().includes(searchQuery) ||
        labelForMode(row).toLowerCase().includes(searchQuery);

      const matchesBucket =
        enabledBuckets.has(row.bucket);

      let matchesCategory = true;
      if (row.category === "Vehicle") {
        matchesCategory = enabledCategories.has("Vehicle");
      }
      if (!enabledCategories.has("E.V.A.") &&
          row.category === "E.V.A.") {
        matchesCategory = false;
      }
      if (!enabledCategories.has("ON FOOT") &&
          row.category === "ON FOOT") {
        matchesCategory = false;
      }

      const matchesCategoryMode =
        (row.category === "Vehicle" && enabledCategories.has("Vehicle")) ||
        (row.category === "E.V.A." && enabledCategories.has("E.V.A.")) ||
        (row.category === "ON FOOT" && enabledCategories.has("ON FOOT"));

      const visible =
        matchesSearch &&
        (matchesBucket || matchesCategoryMode) &&
        matchesCategory;
      item.style.display = visible ? "" : "none";
      item.dataset.localHidden = visible ? "false" : "true";
    });

    getScrollboxes().forEach((scrollbox) => {
      const visibleCount = [...scrollbox.children].filter((item) =>
        getComputedStyle(item).display !== "none"
      ).length;
      scrollbox.style.display = visibleCount ? "" : "none";
    });
  };

  const setButtonActive = (button, active) => {
    if (!button) return;
    button.classList.toggle("bg-primary-container", active);
    button.classList.toggle("text-black", active);
    button.classList.toggle("text-neutral-300", !active);
  };

  const findButton = (text, ariaLabel) => {
    return [...document.querySelectorAll("button")].find((button) => {
      if (ariaLabel) return button.getAttribute("aria-label") === ariaLabel;
      return button.innerText.trim() === text;
    });
  };

  const applyGeometry = () => {
    document.querySelectorAll(".stv-geo").forEach((container) => {
      if (!container.querySelector(
        ":scope > img.local-geometry, :scope > svg.local-inline-geometry",
      )) {
        const image = document.createElement("img");
        image.className = "local-geometry";
        image.src = "charts/vkb-gladiator-dual.geometry.svg";
        image.alt = "";
        image.setAttribute("aria-hidden", "true");
        container.appendChild(image);

        fetch("charts/vkb-gladiator-dual.geometry.svg")
          .then((response) => response.text())
          .then((source) => {
            const parsed = new DOMParser().parseFromString(
              source,
              "image/svg+xml",
            );
            const svg = parsed.documentElement;
            svg.setAttribute("class", "local-inline-geometry");
            svg.setAttribute("aria-hidden", "true");
            container.querySelector("img.local-geometry")?.remove();
            container.appendChild(document.importNode(svg, true));
            applyFilters();
          })
          .catch(() => {});
      }

      const content = container.closest(".react-transform-component");
      if (content) content.style.transformOrigin = "0 0";
    });
  };

  const applyInitialFit = () => {
    const chart = document.querySelector(".stv-chart");
    const content = document.querySelector(".react-transform-component");
    if (!chart || !content) return;

    const rect = chart.getBoundingClientRect();
    const scale = Math.min(rect.width / 3840, rect.height / 2160);
    const y = (rect.height - 2160 * scale) / 2;
    zoomScale = scale;
    content.style.transform =
      `translate(0px, ${y}px) scale(${scale})`;
  };

  const setZoom = (scale) => {
    const chart = document.querySelector(".stv-chart");
    const content = document.querySelector(".react-transform-component");
    if (!chart || !content) return;

    zoomScale = Math.max(0.15, Math.min(4, scale));
    const rect = chart.getBoundingClientRect();
    const y = (rect.height - 2160 * zoomScale) / 2;
    content.style.transform =
      `translate(0px, ${y}px) scale(${zoomScale})`;
  };

  const downloadPNG = async () => {
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 3840;
      canvas.height = 2160;
      const context = canvas.getContext("2d");
      const chart = document.querySelector(".stv-chart");
      context.fillStyle = "#121414";
      context.fillRect(0, 0, 3840, 2160);
      context.drawImage(image, 0, 0, 3840, 2160);

      context.fillStyle = "#ffffff";
      context.font = "700 54px sans-serif";
      context.fillText(
        "VKB Gladiator NXT x2 — " + labelMode + " Bindings",
        120,
        140,
      );

      canvas.toBlob((png) => {
        if (!png) return;
        const pngUrl = URL.createObjectURL(png);
        const link = document.createElement("a");
        link.href = pngUrl;
        link.download = "vkb-gladiator-binding-chart.png";
        link.click();
        setTimeout(() => URL.revokeObjectURL(pngUrl), 1000);
      }, "image/png");
    };

    image.src = "charts/vkb-gladiator-dual.geometry.svg";
  };

  const initialize = () => {
    // Remove the version badge and the Joystick Gremlin logo baked into the chart
    document
      .querySelectorAll('div[data-header="true"]')
      .forEach((el) => {
        if (/^Updated:/.test(el.textContent.trim())) el.remove();
      });
    document
      .querySelectorAll('div[data-jglogo="true"]')
      .forEach((el) => el.remove());

    // Hide the Background (dark/light) and Help sections in the side panel
    document
      .querySelectorAll(".stv-chart div.border-t")
      .forEach((section) => {
        const text = section.textContent.trim();
        if (/^Background/.test(text) || /^Help/.test(text)) {
          section.style.display = "none";
        }
      });

    applyGeometry();
    applyInitialFit();
    applyLabelMode();
    applyFilters();
    applyCvdColors();

    const search = document.querySelector(
      'input[placeholder="Search a bind — press / to focus"]',
    );
    if (search && !search.dataset.localBound) {
      search.dataset.localBound = "true";
      search.addEventListener("input", () => {
        searchQuery = search.value.trim().toLowerCase();
        applyFilters();
      });
    }

    ["Player", "CIG", "Raw"].forEach((mode) => {
      const button = findButton(mode);
      if (!button || button.dataset.localBound) return;
      button.dataset.localBound = "true";
      button.addEventListener("click", () => {
        labelMode = mode;
        ["Player", "CIG", "Raw"].forEach((name) =>
          setButtonActive(findButton(name), name === mode),
        );
        applyLabelMode();
        applyFilters();
      });
    });

    document.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      if (checkbox.dataset.localBound) return;
      checkbox.dataset.localBound = "true";
      checkbox.addEventListener("change", applyFilters);
    });

    const plus = findButton(null, "Zoom in");
    if (plus && !plus.dataset.localBound) {
      plus.dataset.localBound = "true";
      plus.addEventListener("click", () => setZoom(zoomScale * 1.25));
    }

    const minus = findButton(null, "Zoom out");
    if (minus && !minus.dataset.localBound) {
      minus.dataset.localBound = "true";
      minus.addEventListener("click", () => setZoom(zoomScale / 1.25));
    }

    const fit = findButton("Fit");
    if (fit && !fit.dataset.localBound) {
      fit.dataset.localBound = "true";
      fit.addEventListener("click", applyInitialFit);
    }

    const legendButton = findButton(null, "Hide legend");
    if (legendButton && !legendButton.dataset.localBound) {
      legendButton.dataset.localBound = "true";
      legendButton.addEventListener("click", () => {
        legendHidden = !legendHidden;
        const panel = [...document.querySelectorAll(".stv-chart > div")]
          .find((element) =>
            element.className.includes("absolute right-0"));
        if (panel) {
          panel.style.transform =
            legendHidden
              ? "translateY(-50%) translateX(221px)"
              : "translateY(-50%) translateX(0)";
        }
        legendButton.setAttribute(
          "aria-label",
          legendHidden ? "Show legend" : "Hide legend",
        );
      });
    }

    const collapse = findButton(null, "Collapse menu");
    if (collapse && !collapse.dataset.localBound) {
      collapse.dataset.localBound = "true";
      collapse.addEventListener("click", () => {
        leftMenuHidden = !leftMenuHidden;
        const leftPanel = collapse.closest(".absolute.left-4");
        if (leftPanel) {
          const children = [...leftPanel.children];
          children.forEach((child, index) => {
            if (index > 0) child.style.display =
              leftMenuHidden ? "none" : "";
          });
          leftPanel.style.width = leftMenuHidden ? "224px" : "";
        }
        collapse.setAttribute(
          "aria-label",
          leftMenuHidden ? "Expand menu" : "Collapse menu",
        );
      });
    }

    const download = findButton("Download PNG");
    if (download && !download.dataset.localBound) {
      download.dataset.localBound = "true";
      download.addEventListener("click", downloadPNG);
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }

  let observerFrame = 0;
  const observer = new MutationObserver(() => {
    if (observerFrame) cancelAnimationFrame(observerFrame);
    observerFrame = requestAnimationFrame(() => {
      applyGeometry();
      applyFilters();
      applyCvdColors();

      document.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
        if (checkbox.dataset.localBound) return;
        checkbox.dataset.localBound = "true";
        checkbox.addEventListener("change", applyFilters);
      });

      document.querySelectorAll(".stv-scrollbox").forEach((scrollbox) => {
        const visibleCount = [...scrollbox.children].filter((item) =>
          getComputedStyle(item).display !== "none"
        ).length;
        if (visibleCount === 0) {
          scrollbox.dataset.localHidden = "true";
          scrollbox.style.setProperty("display", "none", "important");
        }
      });
    });
  });
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["style", "class", "checked"],
  });
})();
