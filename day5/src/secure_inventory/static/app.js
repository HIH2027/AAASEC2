"use strict";

const runButton = document.getElementById("run");
const statusLine = document.getElementById("status");
const results = document.getElementById("results");
const rows = document.getElementById("rows");

function selectedMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function setStatus(message, isError) {
  statusLine.textContent = message;
  statusLine.classList.toggle("error", Boolean(isError));
}

function cell(text, className) {
  const td = document.createElement("td");
  // textContent, never innerHTML: item names are untrusted data.
  td.textContent = text;
  if (className) {
    td.className = className;
  }
  return td;
}

function renderRows(items) {
  rows.replaceChildren();
  for (const item of items) {
    const tr = document.createElement("tr");
    tr.append(
      cell(item.name),
      cell(item.qty, "num"),
      cell(item.unit_cost_sar, "num"),
      cell(item.total_value_sar, "num")
    );

    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = item.low_stock ? "badge low" : "badge ok";
    badge.textContent = item.low_stock ? "LOW STOCK" : "OK";
    statusCell.append(badge);
    tr.append(statusCell);

    rows.append(tr);
  }
}

function render(result) {
  const analysis = result.analysis;
  document.getElementById("total").textContent =
    `${analysis.grand_total_sar.toLocaleString("en-US")} SAR`;
  document.getElementById("low-count").textContent = analysis.low_stock_items.length;
  document.getElementById("mode-used").textContent =
    result.mode === "live" ? "Live AI" : "Offline";
  renderRows(analysis.items);
  document.getElementById("recommendation").textContent = result.recommendation;
  results.hidden = false;
}

async function runAnalysis() {
  const mode = selectedMode();
  runButton.disabled = true;
  setStatus(mode === "live" ? "Asking the model..." : "Running the agent...", false);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    const payload = await response.json();

    if (!response.ok) {
      setStatus(payload.error || `Request failed (${response.status})`, true);
      return;
    }

    render(payload);
    setStatus(`Analysis complete in ${mode} mode.`, false);
  } catch (error) {
    setStatus(`Could not reach the dashboard backend: ${error.message}`, true);
  } finally {
    runButton.disabled = false;
  }
}

runButton.addEventListener("click", runAnalysis);
