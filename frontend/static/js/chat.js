/*
 * Chat frontend logic: sends queries to the Flask JSON API, renders
 * markdown responses, and embeds Vega-Lite charts produced by the agent's
 * chart tools (serialized server-side from ChartState).
 */

(function () {
  const messagesEl = document.getElementById("chat-messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const spinner = document.getElementById("chat-spinner");

  function renderMarkdown(el) {
    if (window.marked) {
      el.innerHTML = window.marked.parse(el.textContent);
    }
  }

  function renderChart(el) {
    if (!window.vegaEmbed) return;
    let spec;
    try {
      spec = JSON.parse(el.dataset.spec);
    } catch (e) {
      el.textContent = "Failed to parse chart specification.";
      return;
    }
    window.vegaEmbed(el, spec, { actions: false }).catch(function (err) {
      el.textContent = "Failed to render chart: " + err.message;
    });
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function appendMessage(message) {
    const wrapper = document.createElement("div");
    wrapper.className = "chat-message " + message.role;

    const role = document.createElement("div");
    role.className = "chat-role";
    role.textContent = message.role === "user" ? "You" : "Assistant";
    wrapper.appendChild(role);

    const content = document.createElement("div");
    content.className = "chat-content markdown-body";
    content.textContent = message.content;
    renderMarkdown(content);
    wrapper.appendChild(content);

    (message.charts || []).forEach(function (chart) {
      if (chart.spec) {
        const container = document.createElement("div");
        container.className = "chart-container";
        const chartEl = document.createElement("div");
        chartEl.className = "chart";
        chartEl.dataset.spec = JSON.stringify(chart.spec);
        container.appendChild(chartEl);
        wrapper.appendChild(container);
        renderChart(chartEl);
      } else {
        const note = document.createElement("div");
        note.className = "alert alert-info";
        note.textContent =
          "Chart '" + (chart.title || "Unknown") + "' has no data to display";
        wrapper.appendChild(note);
      }
    });

    messagesEl.appendChild(wrapper);
    scrollToBottom();
  }

  function setBusy(busy) {
    spinner.classList.toggle("hidden", !busy);
    input.disabled = busy;
    form.querySelector("button").disabled = busy;
    if (!busy) input.focus();
  }

  async function sendQuery(query) {
    appendMessage({ role: "user", content: query, charts: [] });
    setBusy(true);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query }),
      });
      const data = await response.json();
      if (data.ok) {
        appendMessage(data.message);
      } else {
        appendMessage({
          role: "assistant",
          content: "Error: " + (data.error || "Unknown error"),
          charts: [],
        });
      }
    } catch (err) {
      appendMessage({
        role: "assistant",
        content: "Error: failed to reach the backend (" + err.message + ")",
        charts: [],
      });
    } finally {
      setBusy(false);
    }
  }

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const query = input.value.trim();
      if (!query) return;
      input.value = "";
      sendQuery(query);
    });
  }

  document.querySelectorAll(".example-query").forEach(function (button) {
    button.addEventListener("click", function () {
      if (input && !input.disabled) {
        sendQuery(button.dataset.query);
      }
    });
  });

  // Render server-side transcript (markdown + charts) on page load.
  document
    .querySelectorAll("#chat-messages .chat-content[data-markdown]")
    .forEach(renderMarkdown);
  document
    .querySelectorAll("#chat-messages .chart[data-spec]")
    .forEach(renderChart);
  scrollToBottom();
})();
