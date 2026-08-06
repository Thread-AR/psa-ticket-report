"use strict";

const STEPS = [
  { key: "psa", label: "PSA" },
  { key: "setup", label: "Setup" },
  { key: "credentials", label: "Credentials" },
  { key: "options", label: "Options" },
  { key: "output", label: "Output" },
  { key: "review", label: "Review" },
  { key: "run", label: "Run" },
];

const state = {
  psas: [],
  psaKey: null,
  psaCfg: null,
  creds: {},
  days: 90,
  boards: [],
  selectedBoardIds: new Set(),
  boardsLoaded: false,
  manualMode: false,
  manualBoardsText: "",
  outputDir: null,
  running: false,
};

function api() {
  return window.pywebview.api;
}

function $(sel) {
  return document.querySelector(sel);
}

function showScreen(name) {
  document.querySelectorAll(".screen").forEach((el) => {
    el.classList.toggle("active", el.dataset.screen === name);
  });
  renderStepper(name);
}

function renderStepper(activeKey) {
  const activeIdx = STEPS.findIndex((s) => s.key === activeKey);
  const stepper = $("#stepper");
  stepper.innerHTML = "";
  STEPS.forEach((step, i) => {
    const el = document.createElement("div");
    el.className = "step" + (i === activeIdx ? " active" : i < activeIdx ? " done" : "");
    el.innerHTML = `<span class="dot"></span><span>${step.label}</span>`;
    stepper.appendChild(el);
  });
}

// ---------------------------------------------------------------------
// Screen: PSA select
// ---------------------------------------------------------------------

function renderPsaCards() {
  const container = $("#psaCards");
  container.innerHTML = "";
  state.psas.forEach((psa) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "psa-card";
    card.textContent = psa.label;
    card.addEventListener("click", () => selectPsa(psa.key));
    container.appendChild(card);
  });
}

function selectPsa(key) {
  state.psaKey = key;
  state.psaCfg = state.psas.find((p) => p.key === key);
  state.creds = {};
  state.boards = [];
  state.boardsLoaded = false;
  state.selectedBoardIds = new Set();
  renderSetupScreen();
  showScreen("setup");
}

// ---------------------------------------------------------------------
// Screen: Setup instructions
// ---------------------------------------------------------------------

function renderSetupScreen() {
  const cfg = state.psaCfg;
  $("#setupPsaLabel").textContent = cfg.label;
  $("#setupAdminNote").innerHTML = cfg.setup.admin_note;

  const list = $("#setupSteps");
  list.innerHTML = "";
  cfg.setup.steps.forEach((step) => {
    const li = document.createElement("li");
    li.innerHTML = step;
    list.appendChild(li);
  });

  $("#setupResultNote").innerHTML = cfg.setup.result_note;
}

function enterCredentialsScreen() {
  renderCredentialsForm();
  showScreen("credentials");
}

// ---------------------------------------------------------------------
// Screen: Credentials
// ---------------------------------------------------------------------

function renderCredentialsForm() {
  $("#credsPsaLabel").textContent = state.psaCfg.label;
  const form = $("#credsForm");
  form.innerHTML = "";

  state.psaCfg.fields.forEach((field) => {
    const wrap = document.createElement("label");
    wrap.className = "field";

    const labelSpan = document.createElement("span");
    labelSpan.className = "field-label";
    labelSpan.textContent = field.label + (field.optional ? "" : "");
    if (field.optional) {
      const opt = document.createElement("span");
      opt.className = "field-optional";
      opt.textContent = " (optional)";
      labelSpan.appendChild(opt);
    }
    wrap.appendChild(labelSpan);

    if (field.help) {
      const help = document.createElement("p");
      help.className = "field-help";
      help.textContent = field.help;
      wrap.appendChild(help);
    }

    const input = document.createElement("input");
    input.type = field.secret ? "password" : "text";
    input.placeholder = field.placeholder || "";
    input.value = state.creds[field.key] || "";
    input.dataset.key = field.key;
    input.addEventListener("input", () => {
      state.creds[field.key] = input.value;
      updateCredsContinueState();
    });
    wrap.appendChild(input);

    form.appendChild(wrap);
  });

  updateCredsContinueState();
}

function updateCredsContinueState() {
  const allFilled = state.psaCfg.fields
    .filter((f) => !f.optional)
    .every((f) => (state.creds[f.key] || "").trim().length > 0);
  $("#credsContinue").disabled = !allFilled;
}

// ---------------------------------------------------------------------
// Screen: Options (days + board exclusions)
// ---------------------------------------------------------------------

function enterOptionsScreen() {
  $("#boardTermPlural").textContent = state.psaCfg.board_term_plural.toLowerCase();
  $("#boardTermPlural2").textContent = state.psaCfg.board_term_plural;
  $("#daysInput").value = state.days;
  renderBoardsList();
  showScreen("options");
}

function renderBoardsList() {
  const list = $("#boardsList");
  list.innerHTML = "";
  state.boards.forEach((board) => {
    const row = document.createElement("label");
    row.className = "board-row";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.selectedBoardIds.has(board.id);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) state.selectedBoardIds.add(board.id);
      else state.selectedBoardIds.delete(board.id);
    });
    const text = document.createElement("span");
    text.textContent = `${board.name} (${board.id})`;
    row.appendChild(checkbox);
    row.appendChild(text);
    list.appendChild(row);
  });
}

async function loadBoards() {
  const statusEl = $("#boardsStatus");
  const btn = $("#loadBoardsBtn");
  btn.disabled = true;
  statusEl.classList.remove("error");
  statusEl.textContent = "Loading…";

  const result = await api().list_boards(state.psaKey, state.creds);
  btn.disabled = false;

  if (!result.ok) {
    statusEl.classList.add("error");
    statusEl.textContent = result.error;
    $("#manualBoardsToggle").checked = true;
    toggleManualBoards(true);
    return;
  }

  state.boards = result.boards;
  state.boardsLoaded = true;
  statusEl.textContent = `Found ${result.boards.length} ${state.psaCfg.board_term_plural.toLowerCase()}.`;
  renderBoardsList();
}

function toggleManualBoards(on) {
  state.manualMode = on;
  $("#manualBoardsInput").disabled = !on;
  $("#boardsList").style.display = on ? "none" : "";
  $("#loadBoardsBtn").style.display = on ? "none" : "";
}

function excludedBoardsValue() {
  if (state.manualMode) {
    return $("#manualBoardsInput").value.trim();
  }
  return Array.from(state.selectedBoardIds).join(",");
}

// ---------------------------------------------------------------------
// Screen: Output folder
// ---------------------------------------------------------------------

async function enterOutputScreen() {
  if (!state.outputDir) {
    state.outputDir = await api().default_output_dir();
  }
  $("#outputPathDisplay").textContent = state.outputDir;
  $("#outputContinue").disabled = !state.outputDir;
  showScreen("output");
}

async function pickFolder() {
  const chosen = await api().pick_output_folder(state.outputDir);
  if (chosen) {
    state.outputDir = chosen;
    $("#outputPathDisplay").textContent = chosen;
  }
  $("#outputContinue").disabled = !state.outputDir;
}

// ---------------------------------------------------------------------
// Screen: Review
// ---------------------------------------------------------------------

function enterReviewScreen() {
  const excluded = excludedBoardsValue();
  const rows = [
    ["PSA", state.psaCfg.label],
    ["Lookback window", `${state.days} days`],
    [
      `Excluded ${state.psaCfg.board_term_plural.toLowerCase()}`,
      excluded ? excluded : "None",
    ],
    ["Output folder", state.outputDir],
  ];
  const card = $("#reviewCard");
  card.innerHTML = "";
  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "review-row";
    row.innerHTML = `<span class="label">${label}</span><span class="value"></span>`;
    row.querySelector(".value").textContent = value;
    card.appendChild(row);
  });
  showScreen("review");
}

// ---------------------------------------------------------------------
// Screen: Run + Done/Error
// ---------------------------------------------------------------------

window.appendLog = function (line) {
  const panel = $("#logPanel");
  panel.textContent += line + "\n";
  panel.scrollTop = panel.scrollHeight;
};

async function generateReport() {
  state.days = parseInt($("#daysInput").value, 10) || 90;
  const excluded = excludedBoardsValue();

  $("#logPanel").textContent = "";
  state.running = true;
  showScreen("run");

  const result = await api().run_report(
    state.psaKey,
    state.creds,
    state.days,
    excluded,
    state.outputDir
  );
  state.running = false;

  if (result.ok) {
    $("#reportPathDisplay").textContent = result.report_path;
    $("#mappingPathDisplay").textContent = result.mapping_path;
    $("#doneSuccess").style.display = "";
    $("#doneError").style.display = "none";
    state.lastResult = result;
  } else {
    $("#errorMessage").textContent = result.error;
    $("#doneSuccess").style.display = "none";
    $("#doneError").style.display = "";
  }
  showScreen("done");
}

function startOver() {
  state.psaKey = null;
  state.psaCfg = null;
  state.creds = {};
  state.boards = [];
  state.selectedBoardIds = new Set();
  state.boardsLoaded = false;
  state.manualMode = false;
  showScreen("psa");
}

// ---------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------

function wireEvents() {
  document.body.addEventListener("click", (e) => {
    const action = e.target.dataset && e.target.dataset.action;
    if (!action) return;
    switch (action) {
      case "back-to-psa":
        showScreen("psa");
        break;
      case "to-credentials":
        enterCredentialsScreen();
        break;
      case "back-to-setup":
        showScreen("setup");
        break;
      case "back-to-credentials":
        showScreen("credentials");
        break;
      case "to-output":
        enterOutputScreen();
        break;
      case "back-to-options":
        enterOptionsScreen();
        break;
      case "back-to-output":
        enterOutputScreen();
        break;
      case "back-to-review":
        enterReviewScreen();
        break;
      case "start-over":
        startOver();
        break;
    }
  });

  $("#credsContinue").addEventListener("click", enterOptionsScreen);
  $("#loadBoardsBtn").addEventListener("click", loadBoards);
  $("#manualBoardsToggle").addEventListener("change", (e) => toggleManualBoards(e.target.checked));
  $("#pickFolderBtn").addEventListener("click", pickFolder);
  $("#outputContinue").addEventListener("click", enterReviewScreen);
  $("#generateBtn").addEventListener("click", generateReport);
  $("#openFolderBtn").addEventListener("click", () => api().open_folder(state.outputDir));
}

async function init() {
  wireEvents();
  state.psas = await api().list_psas();
  renderPsaCards();
  showScreen("psa");
}

window.addEventListener("pywebviewready", init);
