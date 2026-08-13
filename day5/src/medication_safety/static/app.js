"use strict";

const runButton = document.getElementById("run");
const statusLine = document.getElementById("status");
const results = document.getElementById("results");

function selectedMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function setStatus(message, isError) {
  statusLine.textContent = message;
  statusLine.classList.toggle("error", Boolean(isError));
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    // textContent, never innerHTML: every value here is untrusted data.
    node.textContent = text;
  }
  return node;
}

function fillList(id, items, emptyText) {
  const list = document.getElementById(id);
  list.replaceChildren();
  if (!items.length) {
    list.append(element("li", null, emptyText));
    return;
  }
  for (const item of items) {
    list.append(element("li", null, item));
  }
}

function renderProfile(profileSummary) {
  const body = document.getElementById("profile-rows");
  body.replaceChildren();
  for (const [label, value] of Object.entries(profileSummary)) {
    const row = document.createElement("tr");
    row.append(element("td", "field", label));
    const absent = value === "Not provided";
    row.append(element("td", absent ? "absent" : null, value));
    body.append(row);
  }
}

function renderFinding(finding) {
  const box = element("div", `finding ${finding.severity}`);

  const head = element("div", "finding-head");
  head.append(element("span", "finding-pair", finding.medications.join(" + ")));
  head.append(element("span", `badge ${finding.severity}`, finding.severity));
  head.append(element("span", "badge action", finding.action_class));
  head.append(element("span", "badge rule", finding.rule_id));
  box.append(head);

  box.append(element("p", "label", "Reason"));
  box.append(element("p", null, finding.reason));
  box.append(element("p", "label", "Clinician action"));
  box.append(element("p", null, finding.action));
  box.append(element("p", "label", "Sources"));

  const list = document.createElement("ul");
  for (const url of finding.sources) {
    const item = document.createElement("li");
    const link = element("a", null, url);
    // Sources come from the rule table, never from the model.
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    item.append(link);
    list.append(item);
  }
  box.append(list);
  return box;
}

function renderFindings(findings) {
  const container = document.getElementById("findings");
  container.replaceChildren();

  if (!findings.length) {
    container.append(
      element(
        "div",
        "empty",
        "No verified rule matched. This does not mean no interaction exists — " +
          "unmatched pairs still require verification in the authorised " +
          "interaction reference and current labelling."
      )
    );
    return;
  }

  for (const finding of findings) {
    container.append(renderFinding(finding));
  }
}

function render(result) {
  const assessment = result.assessment;
  const findings = assessment.findings;

  document.getElementById("finding-count").textContent = findings.length;
  document.getElementById("top-severity").textContent = findings.length
    ? findings[0].severity
    : "None";
  document.getElementById("summary-source").textContent =
    result.summary_source === "model" ? "Model phrasing" : "Deterministic";
  document.getElementById("summary").textContent = result.summary;

  renderProfile(assessment.profile_summary);
  renderFindings(findings);

  fillList("modifiers", assessment.patient_modifiers, "None.");
  fillList(
    "missing",
    assessment.missing_information,
    "None; all requested parameters were supplied."
  );
  fillList("boundary", assessment.boundary, "");

  const inrBlock = document.getElementById("inr-block");
  inrBlock.hidden = assessment.inr_context.length === 0;
  if (assessment.inr_context.length) {
    fillList("inr-context", assessment.inr_context, "");
  }

  results.hidden = false;
}

async function runReview() {
  const mode = selectedMode();
  runButton.disabled = true;
  setStatus(mode === "live" ? "Asking the model to phrase..." : "Applying rules...", false);

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
    setStatus(`Review complete in ${mode} mode.`, false);
  } catch (error) {
    setStatus(`Could not reach the dashboard backend: ${error.message}`, true);
  } finally {
    runButton.disabled = false;
  }
}

runButton.addEventListener("click", runReview);
