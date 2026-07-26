/*
 * Import page behaviour. Two independent pieces, each a no-op when its markup
 * is absent:
 *
 *   1. Live import progress -- polls the backend for the running job's
 *      snapshot and updates the progress bar and per-file status list in
 *      place, reloading the page when the job finishes so the server-rendered
 *      results panel appears.
 *   2. Garmin dive checklist -- bulk selection controls and a live count.
 *
 * Everything is written with textContent -- file names and error strings come
 * from disk and from Garmin, and must never be interpreted as markup.
 */

// --- 1. Live import progress -------------------------------------------------

(function () {
  const panel = document.getElementById("import-progress");
  if (!panel) return;

  const progressUrl = panel.dataset.progressUrl;
  const bar = document.getElementById("progress-bar");
  const count = document.getElementById("progress-count");
  const current = document.getElementById("progress-current");
  const list = document.getElementById("progress-items");

  const POLL_INTERVAL_MS = 700;

  function statusRow(item) {
    const row = document.createElement("li");
    row.className = "status-row status-" + item.status;

    const name = document.createElement("span");
    name.className = "status-name";
    name.textContent = item.name;
    row.appendChild(name);

    const detail = document.createElement("span");
    detail.className = "status-detail";
    detail.textContent = item.detail;
    row.appendChild(detail);

    return row;
  }

  function render(job) {
    bar.max = job.total;
    bar.value = job.done;
    count.textContent = job.done + " / " + job.total;
    current.textContent = job.current
      ? "Processing: " + job.current
      : "Starting...";

    // Rows already drawn are never rewritten, so only append the new tail.
    for (let i = list.children.length; i < job.items.length; i++) {
      list.appendChild(statusRow(job.items[i]));
    }
    list.scrollTop = list.scrollHeight;
  }

  async function poll() {
    try {
      const response = await fetch(progressUrl);
      const data = await response.json();

      // No job left means another page load already harvested the results.
      if (!data.ok || !data.job) {
        window.location.reload();
        return;
      }

      render(data.job);

      if (data.job.finished) {
        window.location.reload();
        return;
      }
    } catch (err) {
      // Transient failure while the worker is busy: keep polling.
    }
    window.setTimeout(poll, POLL_INTERVAL_MS);
  }

  poll();
})();


// --- 2. Garmin dive checklist ------------------------------------------------

(function () {
  const form = document.getElementById("garmin-import-form");
  if (!form) return;

  const boxes = Array.from(form.querySelectorAll('input[name="dive_ids"]'));
  const counter = document.getElementById("dive-selection-count");
  if (!boxes.length) return;

  function updateCount() {
    const selected = boxes.filter((box) => box.checked).length;
    counter.textContent = `${selected} of ${boxes.length} selected`;
  }

  form.querySelectorAll("[data-select]").forEach(function (button) {
    button.addEventListener("click", function () {
      const mode = button.dataset.select;
      boxes.forEach(function (box) {
        // "new" restores the default: everything Garmin has not already been
        // imported from, which is what the page loads with.
        box.checked =
          mode === "all" ? true : mode === "new" ? !box.dataset.imported : false;
      });
      updateCount();
    });
  });

  boxes.forEach(function (box) {
    box.addEventListener("change", updateCount);
  });

  updateCount();
})();
