"use strict";

// Every value rendered here is untrusted: it comes from operator input or from
// the MCP service. Nothing is ever assigned through innerHTML.

const PARAM_SLOTS = [
  { key: "age", label: "Age", type: "number", min: 0, max: 120 },
  { key: "bmi", label: "BMI", type: "number", step: "0.1", min: 8, max: 90 },
  { key: "bsa", label: "BSA (m^2)", type: "number", step: "0.01", min: 0.3, max: 4 },
  { key: "warfarin_indication", label: "Indication for warfarin", type: "text" },
  { key: "dvt_timing", label: "DVT timing", type: "text" },
  { key: "inr", label: "INR", type: "number", step: "0.1" },
  { key: "egfr", label: "eGFR", type: "number" },
  { key: "crcl", label: "CrCl", type: "number" },
  { key: "serum_creatinine", label: "Serum creatinine", type: "number", step: "0.1" },
  { key: "liver_status", label: "Liver status", type: "text" },
  { key: "potassium", label: "Potassium", type: "number", step: "0.1" },
  { key: "magnesium", label: "Magnesium", type: "number", step: "0.1" },
  { key: "qtc_ms", label: "QTc (ms)", type: "number" },
  { key: "heart_rate", label: "Heart rate", type: "number" },
  { key: "digoxin_level", label: "Digoxin level", type: "number", step: "0.1" },
  { key: "cbc_hemoglobin", label: "CBC/hemoglobin", type: "number", step: "0.1" },
  {
    key: "aspirin_clopidogrel_indication",
    label: "Aspirin/clopidogrel indication",
    type: "text",
  },
];

const SUGGESTIONS = [
  "Which finding is most urgent?",
  "What information is missing?",
  "Why is warfarin flagged?",
  "What do the patient modifiers mean?",
];

let currentAssessment = null;
let lastMode = "offline";
const chatHistory = [];

const statusLine = document.getElementById("status");
const chatStatus = document.getElementById("chat-status");
const results = document.getElementById("results");
const chatSection = document.getElementById("chat-section");
const chatLog = document.getElementById("chat-log");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function selectedMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function setStatus(target, message, isError) {
  target.textContent = message;
  target.classList.toggle("error", Boolean(isError));
}

/* ---------- step 1: input slots ---------- */

function addMedicationRow(medication = {}) {
  const row = element("div", "med-row");
  // Placement is the stylesheet's job; data-key drives both the grid areas
  // and the profile that collectProfile() builds.
  const fields = [
    { key: "name", placeholder: "Medication name" },
    { key: "dose", placeholder: "Dose" },
    { key: "frequency", placeholder: "Frequency" },
    { key: "route", placeholder: "Route" },
  ];

  for (const field of fields) {
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = field.placeholder;
    input.dataset.key = field.key;
    input.value = medication[field.key] || "";
    row.append(input);
  }

  const remove = element("button", "secondary small", "×");
  remove.type = "button";
  remove.title = "Remove this medication";
  remove.addEventListener("click", () => {
    row.remove();
    if (!document.querySelectorAll(".med-row").length) addMedicationRow();
  });
  row.append(remove);

  document.getElementById("med-slots").append(row);
}

function buildParamSlots() {
  const grid = document.getElementById("param-slots");
  for (const slot of PARAM_SLOTS) {
    const wrapper = element("label", "slot");
    wrapper.append(element("span", "slot-label", slot.label));

    const input = document.createElement("input");
    input.type = slot.type;
    input.id = `slot-${slot.key}`;
    input.placeholder = "Not provided";
    if (slot.min !== undefined) input.min = slot.min;
    if (slot.max !== undefined) input.max = slot.max;
    if (slot.step) input.step = slot.step;
    wrapper.append(input);
    grid.append(wrapper);
  }

  const wrapper = element("label", "slot");
  wrapper.append(element("span", "slot-label", "Dialysis"));
  const select = document.createElement("select");
  select.id = "slot-dialysis";
  for (const [value, text] of [["", "Not provided"], ["true", "Yes"], ["false", "No"]]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.append(option);
  }
  wrapper.append(select);
  grid.append(wrapper);
}

function collectProfile() {
  const profile = {};

  for (const slot of PARAM_SLOTS) {
    const raw = document.getElementById(`slot-${slot.key}`).value.trim();
    if (!raw) continue;
    profile[slot.key] = slot.type === "number" ? Number(raw) : raw;
  }

  const dialysis = document.getElementById("slot-dialysis").value;
  if (dialysis) profile.dialysis = dialysis === "true";

  const description = document.getElementById("slot-patient_description").value.trim();
  if (description) profile.patient_description = description;

  const medications = [];
  for (const row of document.querySelectorAll(".med-row")) {
    const medication = {};
    for (const input of row.querySelectorAll("input")) {
      const value = input.value.trim();
      if (value) medication[input.dataset.key] = value;
    }
    if (medication.name) medications.push(medication);
  }
  profile.medications = medications;
  return profile;
}

function fillSlots(profile) {
  for (const slot of PARAM_SLOTS) {
    const value = profile[slot.key];
    const absent = value === null || value === undefined || value === "Not provided";
    document.getElementById(`slot-${slot.key}`).value = absent ? "" : value;
  }
  const dialysis = profile.dialysis;
  document.getElementById("slot-dialysis").value =
    dialysis === true ? "true" : dialysis === false ? "false" : "";

  const description = profile.patient_description;
  document.getElementById("slot-patient_description").value =
    description && description !== "Not provided" ? description : "";

  document.getElementById("med-slots").replaceChildren();
  const medications = profile.medications || [];
  if (!medications.length) addMedicationRow();
  for (const medication of medications) addMedicationRow(medication);
  updateParamCount();
}

/* ---------- upload: fill the slots from a document ---------- */

function renderExtractReport(result) {
  const box = document.getElementById("extract-report");
  box.replaceChildren();
  box.hidden = false;
  box.classList.toggle(
    "warn",
    result.unrecognised.length > 0 || result.recognised.length === 0
  );

  box.append(element("h4", null, `Read from ${result.source}`));

  const medications = (result.profile.medications || []).length;
  box.append(
    element(
      "p",
      null,
      `${medications} medication(s) and ` +
        `${result.recognised.length - medications} parameter(s) filled in. ` +
        "Check them before running."
    )
  );

  if (result.unrecognised.length) {
    box.append(
      element("p", "flag", "Not recognised — add by hand if they are medicines:")
    );
    const list = document.createElement("ul");
    for (const line of result.unrecognised.slice(0, 6)) {
      list.append(element("li", "flag", line));
    }
    box.append(list);
  }

  for (const note of result.notes) {
    box.append(element("p", null, note));
  }
}

async function uploadFile(file) {
  if (!file) return;

  const dropzone = document.getElementById("dropzone");
  dropzone.classList.add("busy");
  setStatus(statusLine, `Reading ${file.name}...`, false);

  const body = new FormData();
  body.append("file", file);

  try {
    const response = await fetch("/api/extract", { method: "POST", body });
    const payload = await response.json();

    if (!response.ok) {
      document.getElementById("extract-report").hidden = true;
      setStatus(statusLine, payload.error || `Upload failed (${response.status})`, true);
      return;
    }

    fillSlots(payload.profile);
    renderExtractReport(payload);
    // Open the parameter disclosure when the upload actually filled some.
    if (payload.recognised.length > (payload.profile.medications || []).length) {
      document.getElementById("param-details").open = true;
    }
    setStatus(statusLine, "Slots filled from the upload. Review, then run.", false);
  } catch (error) {
    setStatus(statusLine, `Could not upload: ${error.message}`, true);
  } finally {
    dropzone.classList.remove("busy");
  }
}

/* ---------- welcome ---------- */

const WELCOME_KEY = "medsafety-seen-welcome";

function closeWelcome() {
  document.getElementById("welcome").hidden = true;
  try {
    localStorage.setItem(WELCOME_KEY, "1");
  } catch (error) {
    // Storage can be refused; the greeting simply shows again next visit.
  }
}

function initWelcome() {
  let seen = null;
  try {
    seen = localStorage.getItem(WELCOME_KEY);
  } catch (error) {
    seen = null;
  }
  if (seen) return;

  const backdrop = document.getElementById("welcome");
  backdrop.hidden = false;
  document.getElementById("welcome-start").focus();

  document.getElementById("welcome-start").addEventListener("click", closeWelcome);
  document.getElementById("welcome-sample").addEventListener("click", () => {
    closeWelcome();
    document.getElementById("load-sample").click();
  });
  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) closeWelcome();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !backdrop.hidden) closeWelcome();
  });
}

/* ---------- theme ---------- */

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.getElementById("theme-icon").textContent =
    theme === "dark" ? "☀" : "☽";
  try {
    localStorage.setItem("medsafety-theme", theme);
  } catch (error) {
    // Private browsing can refuse storage; the toggle still works this session.
  }
}

function initTheme() {
  let stored = null;
  try {
    stored = localStorage.getItem("medsafety-theme");
  } catch (error) {
    stored = null;
  }
  // Light by default: this is a document to read, not a code editor.
  applyTheme(stored === "dark" ? "dark" : "light");
}

/* ---------- step 2: rendering the assessment ---------- */

function fillList(id, items, emptyText) {
  const list = document.getElementById(id);
  list.replaceChildren();
  if (!items.length) {
    list.append(element("li", null, emptyText));
    return;
  }
  for (const item of items) list.append(element("li", null, item));
}

function renderProfile(profileSummary) {
  const body = document.getElementById("profile-rows");
  body.replaceChildren();
  for (const [label, value] of Object.entries(profileSummary)) {
    const row = document.createElement("tr");
    row.append(element("td", "field", label));
    row.append(element("td", value === "Not provided" ? "absent" : null, value));
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

  // Sources are collapsed by default: they are long URLs that would otherwise
  // dominate the card, but they stay one click away rather than hidden.
  const sources = document.createElement("details");
  const count = finding.sources.length;
  sources.append(
    element("summary", null, `${count} source${count === 1 ? "" : "s"}`)
  );

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
  sources.append(list);
  box.append(sources);
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
  for (const finding of findings) container.append(renderFinding(finding));
}

const VERDICT_CLASS = {
  "STOP AND CONFIRM": "critical",
  "URGENT REVIEW": "critical",
  "REVIEW SOON": "warn",
  "MONITOR CLOSELY": "warn",
  "ROUTINE CHECK": "ok",
  "NO ACTION NEEDED": "ok",
};

function renderPlan(assessment) {
  const block = document.getElementById("plan-block");
  const hasPlan = assessment.plan_tests.length || assessment.plan_procedures.length;
  block.hidden = !hasPlan;
  if (!hasPlan) return;
  fillList("plan-tests", assessment.plan_tests, "None.");
  fillList("plan-procedures", assessment.plan_procedures, "None.");
}

function resetAiPlanPanel() {
  document.getElementById("ai-plan-result").hidden = true;
  setStatus(document.getElementById("plan-status"), "", false);
  for (const id of ["ai-plan-meds", "ai-plan-tests", "ai-plan-procedures", "ai-plan-notes"]) {
    document.getElementById(id).replaceChildren();
  }
}

function render(result) {
  const assessment = result.assessment;
  const findings = assessment.findings;
  currentAssessment = assessment;
  lastMode = result.mode;

  document.getElementById("verdict-badge").textContent = result.quick_verdict;
  document.getElementById("verdict-badge").className =
    `verdict-badge ${VERDICT_CLASS[result.quick_verdict] || "warn"}`;
  document.getElementById("verdict-source").textContent =
    result.verdict_source === "model" ? "model, constrained" : "deterministic";

  document.getElementById("finding-count").textContent = findings.length;
  document.getElementById("top-severity").textContent = findings.length
    ? findings[0].severity
    : "None";
  document.getElementById("summary-source").textContent =
    result.summary_source === "model" ? "Model phrasing" : "Deterministic";
  document.getElementById("summary").textContent = result.summary;

  renderProfile(assessment.profile_summary);
  renderFindings(findings);
  renderPlan(assessment);
  fillList("modifiers", assessment.patient_modifiers, "None.");
  fillList(
    "missing",
    assessment.missing_information,
    "None; all requested parameters were supplied."
  );
  fillList("boundary", assessment.boundary, "");

  const inrBlock = document.getElementById("inr-block");
  inrBlock.hidden = assessment.inr_context.length === 0;
  if (assessment.inr_context.length) fillList("inr-context", assessment.inr_context, "");

  document.getElementById("placeholder").hidden = true;
  results.hidden = false;
  document.getElementById("ai-plan-section").hidden = false;
  resetAiPlanPanel();
  const generateButton = document.getElementById("generate-plan");
  generateButton.disabled = lastMode !== "live";
  generateButton.title =
    lastMode === "live" ? "" : "Run the review in Live AI mode first";
  chatSection.hidden = false;
}

/* Keeps the collapsed parameter section honest about what is set inside it. */
function updateParamCount() {
  let set = 0;
  for (const slot of PARAM_SLOTS) {
    if (document.getElementById(`slot-${slot.key}`).value.trim()) set += 1;
  }
  if (document.getElementById("slot-dialysis").value) set += 1;
  document.getElementById("param-count").textContent =
    set === 0 ? "none set" : `${set} set`;
}

/* ---------- AI-suggested plan: opt-in, genuinely generated ---------- */

async function generateAiPlan() {
  if (!currentAssessment) return;

  const button = document.getElementById("generate-plan");
  const status = document.getElementById("plan-status");
  button.disabled = true;
  setStatus(status, "Asking the model for suggestions...", false);

  try {
    const response = await fetch("/api/suggest-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: lastMode, assessment: currentAssessment }),
    });
    const payload = await response.json();

    if (!response.ok) {
      setStatus(status, payload.error || `Request failed (${response.status})`, true);
      return;
    }

    const box = document.getElementById("ai-plan-result");
    if (!payload.accepted || !payload.plan) {
      box.hidden = true;
      setStatus(
        status,
        payload.notes?.[0] || "No suggestion passed validation this run.",
        false
      );
      return;
    }

    fillList("ai-plan-meds", payload.plan.medication_considerations, "None suggested.");
    fillList("ai-plan-tests", payload.plan.suggested_tests, "None suggested.");
    fillList("ai-plan-procedures", payload.plan.suggested_procedures, "None suggested.");
    fillList("ai-plan-notes", payload.notes, "");
    document.getElementById("ai-plan-notes").hidden = payload.notes.length === 0;
    box.hidden = false;
    setStatus(status, "Suggestions generated. Confirm every item independently.", false);
  } catch (error) {
    setStatus(status, `Could not reach the backend: ${error.message}`, true);
  } finally {
    button.disabled = lastMode !== "live";
  }
}

/* ---------- step 4: grounded chat ---------- */

function appendMessage(role, text, source) {
  const bubble = element("div", `bubble ${role}`);
  bubble.append(element("p", null, text));
  if (source) {
    const label = source === "model" ? "Model, validated" : "Deterministic";
    bubble.append(element("span", "bubble-source", label));
  }
  chatLog.append(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function askQuestion(question) {
  if (!question || !currentAssessment) return;

  appendMessage("user", question);
  chatHistory.push({ role: "user", content: question });
  document.getElementById("chat-question").value = "";
  document.getElementById("chat-send").disabled = true;
  setStatus(chatStatus, "Thinking...", false);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        mode: selectedMode(),
        assessment: currentAssessment,
        history: chatHistory.slice(0, -1),
      }),
    });
    const payload = await response.json();

    if (!response.ok) {
      setStatus(chatStatus, payload.error || `Request failed (${response.status})`, true);
      return;
    }

    appendMessage("assistant", payload.answer, payload.source);
    chatHistory.push({ role: "assistant", content: payload.answer });
    setStatus(chatStatus, "", false);
  } catch (error) {
    setStatus(chatStatus, `Could not reach the backend: ${error.message}`, true);
  } finally {
    document.getElementById("chat-send").disabled = false;
  }
}

function buildSuggestions() {
  const container = document.getElementById("suggestions");
  for (const text of SUGGESTIONS) {
    const chip = element("button", "chip", text);
    chip.type = "button";
    chip.addEventListener("click", () => askQuestion(text));
    container.append(chip);
  }
}

/* ---------- running the review ---------- */

async function runReview(useMcp) {
  const mode = selectedMode();
  const body = { mode };

  if (!useMcp) {
    const profile = collectProfile();
    if (!profile.medications.length) {
      setStatus(statusLine, "Add at least one medication name first.", true);
      return;
    }
    body.profile = profile;
  }

  document.getElementById("run").disabled = true;
  setStatus(
    statusLine,
    mode === "live" ? "Applying rules, then asking the model to phrase..." : "Applying rules...",
    false
  );

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();

    if (!response.ok) {
      setStatus(statusLine, payload.error || `Request failed (${response.status})`, true);
      return;
    }

    render(payload);
    chatLog.replaceChildren();
    chatHistory.length = 0;
    setStatus(statusLine, `Review complete in ${mode} mode.`, false);
    // On a narrow screen the output sits below the form; scroll it into view.
    if (window.matchMedia("(max-width: 62rem)").matches) {
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (error) {
    setStatus(statusLine, `Could not reach the backend: ${error.message}`, true);
  } finally {
    document.getElementById("run").disabled = false;
  }
}

/* ---------- wiring ---------- */

initTheme();
initWelcome();
buildParamSlots();
addMedicationRow();
buildSuggestions();
updateParamCount();

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener("change", () => {
  uploadFile(fileInput.files[0]);
  fileInput.value = "";
});

for (const name of ["dragenter", "dragover"]) {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  });
}
for (const name of ["dragleave", "drop"]) {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  });
}
dropzone.addEventListener("drop", (event) => {
  uploadFile(event.dataTransfer.files[0]);
});

document.getElementById("theme-toggle").addEventListener("click", () => {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});

document.getElementById("param-slots").addEventListener("input", updateParamCount);
document.getElementById("slot-dialysis").addEventListener("change", updateParamCount);
document.getElementById("add-med").addEventListener("click", () => addMedicationRow());
document.getElementById("run").addEventListener("click", () => runReview(false));
document.getElementById("load-mcp").addEventListener("click", () => runReview(true));

document.getElementById("load-sample").addEventListener("click", async () => {
  setStatus(statusLine, "Loading sample profile...", false);
  try {
    const response = await fetch("/api/sample");
    fillSlots(await response.json());
    setStatus(statusLine, "Sample profile loaded. Run the review.", false);
  } catch (error) {
    setStatus(statusLine, `Could not load the sample: ${error.message}`, true);
  }
});

document.getElementById("generate-plan").addEventListener("click", generateAiPlan);

document.getElementById("clear").addEventListener("click", () => {
  fillSlots({ medications: [] });
  results.hidden = true;
  chatSection.hidden = true;
  document.getElementById("ai-plan-section").hidden = true;
  document.getElementById("placeholder").hidden = false;
  document.getElementById("extract-report").hidden = true;
  currentAssessment = null;
  setStatus(statusLine, "Cleared.", false);
});

document.getElementById("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  askQuestion(document.getElementById("chat-question").value.trim());
});
