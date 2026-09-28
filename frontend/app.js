const API = "http://localhost:8000/api";

const state = {
  type: null,
  docId: null,
  doc: null,
  mode: "swap",
  stage: "type",
  data: {
    students: [],
    faculty: {},
    sourceIds: [],
    images: [],
    papers: [],
    topic: "",
  },
  teamSize: 0,
  reportId: null,
  pendingFile: null,
  currentView: "wizard", // 'wizard' | 'editor'
  activeSection: null,
  reportData: null,
};

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const messages = $("#messages");

window.addEventListener("DOMContentLoaded", () => {
  status();
  $("#send").onclick = submit;
  $("#answer").onkeydown = e => { if (e.key === "Enter") { e.preventDefault(); submit(); } };
  $("#attachment").onchange = e => upload(e.target.files[0]);
  $("#restart").onclick = () => location.reload();
  
  // Editor view triggers
  $("#toggleEditorBtn").onclick = () => switchView("editor");
  $("#backToWizardBtn").onclick = () => switchView("wizard");
  $("#saveDocBtn").onclick = saveDocument;
  $("#downloadDocxBtn").onclick = () => downloadFile("docx");
  $("#downloadPdfBtn").onclick = () => downloadFile("pdf");
  $("#printDocBtn").onclick = () => window.print();
  $("#toolPrint").onclick = () => window.print();

  // AI Copilot triggers
  $("#copilotSendBtn").onclick = sendCopilotMessage;
  $("#copilotInput").onkeydown = e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendCopilotMessage();
    }
  };

  // Quick suggestion chips
  $$(".chip-btn").forEach(btn => {
    btn.onclick = () => {
      const p = btn.dataset.prompt;
      $("#copilotInput").value = p;
      sendCopilotMessage();
    };
  });

  // Rich text formatting toolbar
  initToolbar();

  welcome();
});

async function status() {
  try {
    const r = await fetch(`${API}/status`);
    const d = await r.json();
    $("#status").innerHTML = `<i class="ready"></i>${d.using_ai ? "AI ready" : "Workspace ready"}`;
  } catch {
    $("#status").textContent = "Backend offline";
  }
}

function welcome() {
  bot("What would you like to build?", "Choose a report type to begin. Each will get its own specialised conversation.");
  cards([
    ["PBL report", "Second-year Project Based Learning report", "pbl", 1],
    ["Internship report", "Coming next", "internship", 0],
    ["Final-year project", "Coming next", "final", 0],
    ["Project report", "Coming next", "project", 0],
    ["Seminar report", "Coming next", "seminar", 0]
  ], selectType);
}

function selectType(type, on) {
  if (!on) return bot("That flow is coming next.", "We are perfecting the PBL conversation first.");
  state.type = type;
  state.stage = "reference";
  $("#reportBadge").textContent = "PBL REPORT";
  $("#restart").hidden = false;
  bot("Great — let’s build your PBL report.", "Upload a DOCX college template or completed reference report. I’ll extract the format, college details, faculty designations, chapters, and figure slots.");
  filePrompt("Upload reference DOCX", ".docx", "reference");
}

function bot(title, detail = "") {
  const e = document.createElement("article");
  e.className = "message bot";
  e.innerHTML = `<span class="avatar">AI</span><div><strong>${esc(title)}</strong>${detail ? `<p>${esc(detail)}</p>` : ""}</div>`;
  messages.append(e);
  bottom();
}

function say(text) {
  const e = document.createElement("article");
  e.className = "message user";
  e.innerHTML = `<div>${esc(text)}</div>`;
  messages.append(e);
  bottom();
}

function cards(items, fn) {
  $("#composer").hidden = true;
  const w = document.createElement("div");
  w.className = "choices";
  items.forEach(([t, d, v, on]) => {
    const b = document.createElement("button");
    b.className = "choice";
    b.disabled = !on;
    b.innerHTML = `<strong>${esc(t)}</strong><span>${esc(d)}</span>${on ? "" : "<em>SOON</em>"}`;
    b.onclick = () => fn(v, on);
    w.append(b);
  });
  messages.append(w);
  bottom();
}

function replies(items, fn) {
  $("#composer").hidden = true;
  const w = document.createElement("div");
  w.className = "quick-replies";
  items.forEach(x => {
    const b = document.createElement("button");
    b.textContent = x;
    b.onclick = () => fn(x);
    w.append(b);
  });
  messages.append(w);
  bottom();
}

function filePrompt(label, accept, kind) {
  $("#composer").hidden = true;
  const b = document.createElement("button");
  b.className = "file-prompt";
  b.textContent = `↑  ${label}`;
  b.onclick = () => {
    state.pendingFile = kind;
    const f = $("#attachment");
    f.accept = accept;
    f.click();
  };
  messages.append(b);
  bottom();
}

function ask(question, placeholder, stage, optional = false) {
  state.stage = stage;
  state.pendingFile = null;
  $("#composer").hidden = false;
  $("#answer").placeholder = placeholder;
  bot(question, optional ? "Write “skip” if this is not applicable." : "");
  $("#answer").focus();
  progress();
}

async function upload(file) {
  if (!file) return;
  if (state.pendingFile === "reference") return reference(file);
  if (state.pendingFile === "image") return image(file);
  if (state.pendingFile === "paper") return paper(file);
  if (!/\.(pdf|docx|pptx|txt|md)$/i.test(file.name)) return bot("Please attach PDF, DOCX, PPTX, TXT, or Markdown.");
  say(`Attached ${file.name}`);
  loading("Extracting project facts…");
  const f = new FormData();
  f.append("file", file);
  try {
    const r = await fetch(`${API}/upload-source`, { method: "POST", body: f });
    const d = await r.json();
    removeLoad();
    if (!r.ok) throw Error(d.detail);
    state.data.sourceIds.push(d.source_id);
    bot("Project material added.", `${d.characters_extracted.toLocaleString()} characters are available for report generation.`);
    briefing();
  } catch (e) {
    removeLoad();
    bot("I couldn’t extract that file.", e.message);
  }
}

async function reference(file) {
  if (!/\.docx$/i.test(file.name)) return bot("Please upload a DOCX reference report.");
  say(`Uploaded ${file.name}`);
  loading("Reading the reference format…");
  const f = new FormData();
  f.append("file", file);
  try {
    const r = await fetch(`${API}/upload-doc`, { method: "POST", body: f });
    const d = await r.json();
    removeLoad();
    if (!r.ok) throw Error(d.detail);
    state.docId = d.doc_id;
    state.doc = d;
    state.mode = d.is_template ? "template" : "swap";
    institution(d);
  } catch (e) {
    removeLoad();
    bot("I couldn’t read that document.", e.message);
  }
}

function institution(d) {
  const vals = d.detected_values || {}, clean = v => (v || []).slice().sort((a, b) => a.length - b.length)[0] || "";
  state.data.academicYear = clean(vals.academic_year);
  state.data.collegeName = clean(vals.college_name);
  state.data.departmentName = clean(vals.department_name);
  state.data.universityName = clean(vals.university_name);
  const rows = [
    ["College", state.data.collegeName],
    ["Department", state.data.departmentName],
    ["University", state.data.universityName],
    ["Academic year", state.data.academicYear]
  ].filter(x => x[1]);
  bot("I’ve analysed the reference format.", `${d.total_paragraphs} paragraphs and ${d.total_sections} report sections were found. I’ll use a clean PBL layout based on its college profile and chapter structure.`);
  const c = document.createElement("div");
  c.className = "confirmation";
  c.innerHTML = `<p class="card-label">CONFIRM INSTITUTION DETAILS</p>${rows.map(x => `<div><span>${x[0]}</span><b>${esc(x[1])}</b></div>`).join("") || "<p>The institution fields will remain as they appear in the uploaded template.</p>"}<button>Confirm and continue</button>`;
  c.querySelector("button").onclick = team;
  messages.append(c);
  bottom();
}

function team() {
  bot("Now let’s add your team.");
  replies(["1 member", "2 members", "3 members", "4 members", "5 members", "6 members"], x => {
    state.teamSize = +x[0];
    ask("What is the full name of team member 1?", "e.g. Aditi Sharma", "studentName");
  });
}

function faculty() {
  const roles = state.doc.role_records?.length ? state.doc.role_records : (state.doc.faculty_fields || []).filter(x => x.default_value).map(x => ({ id: x.id, label: x.label, value: x.default_value }));
  if (!roles.length) return ask("Who is your project guide?", "e.g. Prof. R. A. Vasmatkar", "guide");
  bot("I found these faculty details in the reference report.", "Confirm the extracted names and fill any required role that was not found.");
  const f = document.createElement("form");
  f.className = "faculty-form";
  const missingHod = roles.some(x => x.id === "hod_name") ? "" : `<label>Head of Department<input data-id="hod_name" placeholder="Required — e.g. Dr. M. P. Wankhade" required></label>`;
  f.innerHTML = roles.map((x, i) => `<label>${esc(x.label)}<input data-id="${esc(x.id || `role_${i}`)}" value="${attr(x.value || "")}" required></label>`).join("") + missingHod + `<label>Additional designation<input data-id="additional" placeholder="Optional — e.g. PBL coordinator"></label><button>Confirm faculty details</button>`;
  f.onsubmit = e => {
    e.preventDefault();
    f.querySelectorAll("input").forEach(x => {
      if (x.value.trim()) state.data.faculty[x.dataset.id] = x.value.trim();
    });
    ask("What is your PBL project title?", "e.g. Automatic Rooftop Curtain System", "title");
  };
  messages.append(f);
  bottom();
}

function materials() {
  bot("Do you have project material I should analyse?", "Upload a proposal, PPT, notes, source document, or paste a ChatGPT/Claude discussion. Public share links can be included; private links need pasted text or an export. I also auto-find recent relevant papers for your Literature Survey, and you can add your own paper PDFs too.");
  replies(["Upload material", "Upload research papers", "Paste chat/link", "Skip — I’ll explain it"], x => {
    if (x === "Upload material") filePrompt("Attach project material", ".pdf,.docx,.pptx,.txt,.md", "source");
    else if (x === "Upload research papers") filePrompt("Attach research paper PDFs", ".pdf", "paper");
    else if (x === "Paste chat/link") ask("Paste the discussion or public share link.", "Paste conversation text or public link", "chat");
    else briefing();
  });
}

function domainQuestions() {
  if (state.data.domain === "Web application") return ask("Which user types or roles does your project have, and what can each one do?", "e.g. Visitor views information; registered user saves favourites; admin manages content", "webRoles");
  if (state.data.domain === "IoT / Hardware") return ask("Which exact components are you using?", "e.g. Arduino Uno, soil-moisture sensor, relay, 5V pump, 12V power supply", "iotComponents");
  return materials();
}

function briefing() {
  ask("In a few sentences, explain the problem, your solution, and how it works.", "Paste your project briefing here…", "briefing");
}

function evidence() {
  bot("Please add project evidence.", "Upload prototype photos, screenshots, circuit/block diagrams, or result images. I’ll place them into relevant report sections.");
  replies(["Upload images", "I’ll add later"], x => x === "Upload images" ? filePrompt("Upload image", "image/*", "image") : results());
}

async function image(file) {
  if (!file?.type.startsWith("image/")) return bot("Please upload an image file.");
  say(`Uploaded image: ${file.name}`);
  const f = new FormData();
  f.append("file", file);
  try {
    const r = await fetch(`${API}/upload-image`, { method: "POST", body: f });
    const d = await r.json();
    if (!r.ok) throw Error(d.detail);
    state.data.images.push({ image_id: d.image_id, caption: file.name.replace(/\.[^.]+$/, ""), slot_key: "", target_section: "" });
    bot("Image added.");
    replies(["Add another image", "Continue"], x => x.startsWith("Add") ? filePrompt("Upload another image", "image/*", "image") : results());
  } catch (e) {
    bot("Image upload failed.", e.message);
  }
}

async function paper(file) {
  if (!/\.pdf$/i.test(file?.name || "")) return bot("Please upload a PDF research paper.");
  say(`Attached paper: ${file.name}`);
  loading("Reading paper for citation…");
  const f = new FormData();
  f.append("file", file);
  try {
    const r = await fetch(`${API}/upload-paper`, { method: "POST", body: f });
    const d = await r.json();
    removeLoad();
    if (!r.ok) throw Error(d.detail);
    state.data.papers.push({ paper_id: d.paper_id, title: d.title, abstract: d.abstract, authors: d.authors || [], year: d.year, venue: d.venue || "", doi: d.doi });
    bot("Paper added to your Literature Survey.", `${state.data.papers.length} of your own papers will be cited first, then recent papers found for your topic.`);
    replies(["Add another paper", "Continue"], x => x.startsWith("Add") ? filePrompt("Attach research paper PDFs", ".pdf", "paper") : briefing());
  } catch (e) {
    removeLoad();
    bot("I couldn’t read that PDF.", e.message);
  }
}

function results() {
  ask("What result did you observe, test, or demonstrate?", "e.g. Curtains open below 35°C and close above 40°C", "results");
}

function review() {
  state.stage = "review";
  progress(true);
  bot("Your PBL report is ready for review.", "I’ll generate every chapter from confirmed facts and preserve the uploaded document’s layout.");
  const c = document.createElement("section");
  c.className = "review";
  c.innerHTML = `<p class="card-label">REPORT READINESS</p><div><span>Reference format</span><b>✓ Analysed</b></div><div><span>Team</span><b>${state.data.students.length} members</b></div><div><span>Faculty details</span><b>${Object.keys(state.data.faculty).length ? "✓ Confirmed" : "Needs review"}</b></div><div><span>Project evidence</span><b>${state.data.images.length} images</b></div><div><span>Literature survey</span><b>IEEE format</b></div><button>Generate report & open editor</button>`;
  c.querySelector("button").onclick = generate;
  messages.append(c);
  bottom();
}

function submit() {
  const i = $("#answer"), v = i.value.trim();
  if (!v) return;
  i.value = "";
  say(v);
  if (state.stage === "studentName") {
    state.data.students.push({ name: v, roll: "" });
    return ask("What is their roll number or exam-seat number?", "e.g. S190234341", "studentRoll");
  }
  if (state.stage === "studentRoll") {
    state.data.students.at(-1).roll = v.toLowerCase() === "skip" ? "" : v;
    return state.data.students.length < state.teamSize ? ask(`What is the full name of team member ${state.data.students.length + 1}?`, `Team member ${state.data.students.length + 1} full name`, "studentName") : faculty();
  }
  if (state.stage === "guide") {
    state.data.faculty.guide_name = v;
    return ask("What is your HOD’s name?", "Type name or skip", "hod", true);
  }
  if (state.stage === "hod") {
    if (v !== "skip") state.data.faculty.hod_name = v;
    return ask("What is your principal’s name?", "Type name or skip", "principal", true);
  }
  if (state.stage === "principal") {
    if (v !== "skip") state.data.faculty.principal_name = v;
    return ask("What is your PBL project title?", "Project title", "title");
  }
  if (state.stage === "title") {
    state.data.topic = v;
    return ask("Do you have a group number?", "e.g. Group No. 12, or skip", "group", true);
  }
  if (state.stage === "group") {
    if (v !== "skip") state.data.groupNo = v;
    bot("Which domain best describes your project?");
    return replies(["IoT / Hardware", "Web application", "Mobile app", "AI / ML", "Cybersecurity", "Other"], x => {
      state.data.domain = x;
      domainQuestions();
    });
  }
  if (state.stage === "iotComponents") {
    state.data.technology = v;
    return ask("What reading or threshold triggers an action, and how is it stopped?", "e.g. Pump starts below 35% moisture and stops above 55%", "iotLogic");
  }
  if (state.stage === "iotLogic") {
    state.data.controlLogic = v;
    return materials();
  }
  if (state.stage === "webRoles") {
    state.data.roles = v;
    return ask("Describe the main user flow — what does someone do from opening the app to getting the result?", "e.g. User opens the site, picks a beach, sees weather and whether conditions are good to visit", "webFlow");
  }
  if (state.stage === "webFlow") {
    state.data.controlLogic = v;
    return ask("What technology stack and database did you actually use?", "e.g. HTML/CSS/JS, React, Node, Firebase — or write 'not built yet'", "webStack");
  }
  if (state.stage === "webStack") {
    state.data.technology = v;
    return materials();
  }
  if (state.stage === "chat") {
    state.data.chatMaterial = v;
    return briefing();
  }
  if (state.stage === "briefing") {
    state.data.briefing = v;
    return ask("What are the main features and what is already working?", "State only confirmed features; write 'planned' where needed", "technology");
  }
  if (state.stage === "technology") {
    state.data.technology = v;
    return evidence();
  }
  if (state.stage === "results") {
    state.data.results = v;
    bot("I’ll prepare the literature survey from verified, approved sources after the fact sheet is complete.");
    return replies(["Continue to report review"], review);
  }
}

async function generate(e) {
  const b = e.currentTarget;
  b.disabled = true;
  b.textContent = "Generating report…";
  loading("Writing your PBL report and formatting pages…");
  const f = new FormData();
  f.append("doc_id", state.docId);
  f.append("mode", state.mode);
  f.append("report_type", "pbl");
  f.append("topic", state.data.topic);
  f.append("group_no", state.data.groupNo || "");
  f.append("reference_notes", [state.data.briefing, state.data.roles, state.data.controlLogic, state.data.technology, state.data.results, state.data.chatMaterial].filter(Boolean).join("\n\n"));
  Object.entries(state.data.faculty).forEach(x => f.append(x[0], x[1]));
  state.data.students.forEach((x, i) => {
    f.append(`student_name_${i + 1}`, x.name);
    f.append(`roll_no_${i + 1}`, x.roll || "xxxx");
  });
  f.append("source_ids_json", JSON.stringify(state.data.sourceIds));
  f.append("images_json", JSON.stringify(state.data.images));
  f.append("papers_json", JSON.stringify(state.data.papers));

  try {
    const r = await fetch(`${API}/generate`, { method: "POST", body: f });
    const d = await r.json();
    removeLoad();
    if (!r.ok) throw Error(d.detail);
    state.reportId = d.report_id;
    
    bot("Your PBL report is generated and ready in the Document Studio.", "You can edit content live in the Google Docs-style editor with the AI Copilot before downloading.");
    
    const o = document.createElement("div");
    o.className = "output";
    o.innerHTML = `
      <button class="btn-editor-launch" id="btnLaunchEditor">📝 Open Document Studio ↗</button>
      <a href="${API}/download-docx/${d.report_id}">Download DOCX ↓</a>
      <a href="${API}/download-pdf/${d.report_id}">Download PDF ↓</a>
    `;
    o.querySelector("#btnLaunchEditor").onclick = () => switchView("editor");
    messages.append(o);
    bottom();

    $("#toggleEditorBtn").style.display = "inline-flex";
    
    // Automatically switch to online doc editor
    switchView("editor");
  } catch (err) {
    removeLoad();
    bot("The report could not be generated.", err.message);
    b.disabled = false;
    b.textContent = "Try again";
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   ── GOOGLE DOCS STYLE ONLINE DOCUMENT EDITOR CONTROLLER ──
   ═══════════════════════════════════════════════════════════════════════════ */

function switchView(view) {
  state.currentView = view;
  if (view === "editor") {
    $("#wizardView").style.display = "none";
    $("#editorView").style.display = "flex";
    $("#viewIndicator").textContent = "Document Studio Mode";
    $("#toggleEditorBtn").textContent = "← Back to Chat";
    $("#toggleEditorBtn").onclick = () => switchView("wizard");
    if (state.reportId) loadReportToEditor(state.reportId);
  } else {
    $("#editorView").style.display = "none";
    $("#wizardView").style.display = "grid";
    $("#viewIndicator").textContent = "Wizard Mode";
    $("#toggleEditorBtn").textContent = "Open Document Editor ↗";
    $("#toggleEditorBtn").onclick = () => switchView("editor");
  }
}

async function loadReportToEditor(reportId) {
  loading("Loading document into editor…");
  try {
    const res = await fetch(`${API}/report/${reportId}`);
    if (!res.ok) throw Error("Failed to fetch report data");
    const data = await res.json();
    state.reportData = data;
    
    $("#docTitleInput").value = data.topic || "PBL Academic Report";
    renderOutline(data.sections || []);
    renderDocumentCanvas(data);
    removeLoad();
  } catch (e) {
    removeLoad();
    console.error(e);
  }
}

function renderOutline(sections) {
  const nav = $("#outlineNav");
  nav.innerHTML = "";
  
  const standardFront = ["Cover Page", "Certificate", "Acknowledgement", "Abstract", "List of Figures", "Table of Contents"];
  standardFront.forEach(item => {
    const a = document.createElement("a");
    a.className = "outline-item";
    a.textContent = item;
    a.onclick = () => scrollToSection(item);
    nav.append(a);
  });

  sections.forEach(sec => {
    if (sec.toUpperCase() === "ABSTRACT") return;
    const a = document.createElement("a");
    a.className = "outline-item";
    a.textContent = sec;
    a.onclick = () => scrollToSection(sec);
    nav.append(a);
  });
}

function renderDocumentCanvas(data) {
  const container = $("#documentPages");
  container.innerHTML = "";

  const info = data.student_info || {};
  const topic = data.topic || "ACADEMIC PROJECT REPORT";
  const college = info.college_name || "Sinhgad College of Engineering";
  const dept = info.department_name || "Department of Computer Engineering";
  const year = info.academic_year || "2025-26";
  const group = info.group_no || "Group No. 50";
  const students = [];
  for (let i = 1; i <= 6; i++) {
    if (info[`student_name_${i}`]) {
      students.push({ name: info[`student_name_${i}`], seat: info[`roll_no_${i}`] || "xxxx" });
    }
  }

  // 1. Cover Page
  const p1 = createA4Sheet({
    showHeader: false,
    footerLeft: college,
    footerCenter: "I",
    footerRight: dept,
    isFront: true,
  });
  p1.id = "sec-Cover-Page";
  p1.querySelector(".sheet-body").innerHTML = `
    <div class="title-cover-box">
      <div style="font-size:13pt;font-weight:bold;letter-spacing:1px;margin-bottom:12px;">SAVITRIBAI PHULE PUNE UNIVERSITY</div>
      <div style="margin:10px 0;">
        <div style="font-size:14pt;font-weight:bold;">A PBL REPORT ON</div>
        <h1 class="main-title-editable" style="font-size:18pt;font-weight:bold;margin:14px 0 18px 0;line-height:1.4;">${esc(topic.toUpperCase())}</h1>
        <div style="font-size:11pt;line-height:1.6;">SUBMITTED IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR THE AWARD OF THE DEGREE OF<br><strong>BACHELOR OF ENGINEERING (${esc(dept.toUpperCase())})</strong></div>
      </div>
      <div style="margin:16px 0;">
        <div style="font-size:11pt;font-weight:bold;margin-bottom:8pt;">SUBMITTED BY:</div>
        <table style="width:100%;border:none;margin:auto;">
          ${students.map(s => `<tr><td style="border:none;text-align:center;font-weight:bold;font-size:11pt;padding:3pt;">${esc(s.name.toUpperCase())}</td><td style="border:none;text-align:center;font-size:10pt;padding:3pt;">Exam Seat No: ${esc(s.seat)}</td></tr>`).join("")}
        </table>
      </div>
      <div style="margin-top:20px;border-top:2px solid #000;padding-top:12px;">
        <div style="font-size:13pt;font-weight:bold;">${esc(college.toUpperCase())}</div>
        <div style="font-size:11pt;font-weight:bold;">${esc(dept.toUpperCase())}</div>
        <div style="font-size:11pt;font-weight:bold;margin-top:4px;">ACADEMIC YEAR ${esc(year)}</div>
      </div>
    </div>
  `;
  container.append(p1);

  // 2. Certificate Page
  const p2 = createA4Sheet({ showHeader: true, headerLeft: `${topic} | ${group}`, footerLeft: college, footerCenter: "II", footerRight: dept, isFront: true });
  p2.id = "sec-Certificate";
  p2.querySelector(".sheet-body").innerHTML = `
    <h1 class="h1-chapter">CERTIFICATE</h1>
    <p style="margin-top:20pt;line-height:1.8;text-align:justify;">
      This is to certify that the PBL report entitled <strong>“${esc(topic)}”</strong> submitted by 
      ${students.map(s => `<strong>${esc(s.name)}</strong> (${esc(s.seat)})`).join(", ")} is a bonafide work carried out under the guidance of <strong>${esc(info.guide_name || "Project Guide")}</strong> in partial fulfilment of the requirements for the award of Bachelor of Engineering in ${esc(dept)} from Savitribai Phule Pune University during academic year ${esc(year)}.
    </p>
    <div style="margin-top:80pt;display:flex;justify-content:space-between;text-align:center;">
      <div><strong>${esc(info.guide_name || "Project Guide")}</strong><br>Guide</div>
      <div><strong>${esc(info.hod_name || "Dr. M. P. Wankhade")}</strong><br>Head of Department</div>
    </div>
    <div style="margin-top:60pt;text-align:center;">
      <strong>${esc(info.principal_name || "Dr. S. D. Lokhande")}</strong><br>Principal
    </div>
  `;
  container.append(p2);

  // 3. Acknowledgement Page
  const p3 = createA4Sheet({ showHeader: true, headerLeft: `${topic} | ${group}`, footerLeft: college, footerCenter: "III", footerRight: dept, isFront: true });
  p3.id = "sec-Acknowledgement";
  p3.querySelector(".sheet-body").innerHTML = `
    <h1 class="h1-chapter">ACKNOWLEDGEMENT</h1>
    <p style="margin-top:20pt;line-height:1.8;text-align:justify;">
      We express our sincere gratitude to our project guide, <strong>${esc(info.guide_name || "Project Guide")}</strong>, for constant guidance, valuable suggestions, and encouragement throughout the completion of this project.
    </p>
    <p style="line-height:1.8;text-align:justify;">
      We extend our heartfelt gratitude to <strong>${esc(info.hod_name || "Dr. M. P. Wankhade")}</strong>, Head of the Department of ${esc(dept)}, and <strong>${esc(info.principal_name || "Dr. S. D. Lokhande")}</strong>, Principal, for providing excellent academic infrastructure and facilities.
    </p>
    <div style="margin-top:40pt;text-align:right;">
      ${students.map(s => `<div style="font-weight:bold;margin-bottom:4pt;">${esc(s.name)}</div>`).join("")}
    </div>
  `;
  container.append(p3);

  // 4. Abstract Page
  const abstractContent = data.ai_content["Abstract"] || data.ai_content["ABSTRACT"] || "This project presents an innovative engineering solution...";
  const p4 = createA4Sheet({ showHeader: true, headerLeft: `${topic} | ${group}`, footerLeft: college, footerCenter: "IV", footerRight: dept, isFront: true });
  p4.id = "sec-Abstract";
  p4.querySelector(".sheet-body").innerHTML = `
    <h1 class="h1-chapter">ABSTRACT</h1>
    <div class="editable-content-block" data-section="Abstract">
      ${abstractContent.split("\n\n").map(p => `<p>${esc(p)}</p>`).join("")}
    </div>
  `;
  container.append(p4);

  // 5. Table of Contents & List of Figures Page
  const p5 = createA4Sheet({ showHeader: true, headerLeft: `${topic} | ${group}`, footerLeft: college, footerCenter: "V", footerRight: dept, isFront: true });
  p5.id = "sec-Table-of-Contents";
  p5.querySelector(".sheet-body").innerHTML = `
    <h1 class="h1-chapter">TABLE OF CONTENTS</h1>
    <table style="width:100%;border:none;margin-top:14pt;">
      <tr style="font-weight:bold;"><td style="border:none;">Title Page</td><td style="border:none;text-align:right;">I</td></tr>
      <tr style="font-weight:bold;"><td style="border:none;">Certificate</td><td style="border:none;text-align:right;">II</td></tr>
      <tr style="font-weight:bold;"><td style="border:none;">Acknowledgement</td><td style="border:none;text-align:right;">III</td></tr>
      <tr style="font-weight:bold;"><td style="border:none;">Abstract</td><td style="border:none;text-align:right;">IV</td></tr>
      <tr style="font-weight:bold;"><td style="border:none;">Table of Contents</td><td style="border:none;text-align:right;">V</td></tr>
      ${(data.sections || []).filter(s => s.toUpperCase() !== "ABSTRACT").map((s, idx) => `<tr><td style="border:none;padding:4pt 0;">${esc(s)}</td><td style="border:none;text-align:right;">${idx + 1}</td></tr>`).join("")}
    </table>
  `;
  container.append(p5);

  // 6. Section 2: Core Chapters (Numbering restarts at 1)
  let pageNum = 1;
  const sections = (data.sections || []).filter(s => s.toUpperCase() !== "ABSTRACT");
  
  sections.forEach(secName => {
    const content = data.ai_content[secName] || `Technical content for ${secName}...`;
    const pageSheet = createA4Sheet({
      showHeader: true,
      headerLeft: `${topic} | ${group}`,
      footerLeft: college,
      footerCenter: String(pageNum),
      footerRight: dept,
      isFront: false,
    });
    pageSheet.id = `sec-${secName.replace(/[^a-zA-Z0-9]/g, "-")}`;
    
    const isMainChapter = /^(\d+)\s+([A-Z\s]+)/i.test(secName) || /^CHAPTER\s+\d+/i.test(secName);
    
    pageSheet.querySelector(".sheet-body").innerHTML = `
      ${isMainChapter ? `<h1 class="h1-chapter">${esc(secName)}</h1>` : `<h2 class="h2-section">${esc(secName)}</h2>`}
      <div class="editable-content-block" data-section="${attr(secName)}">
        ${content.split("\n\n").map(p => `<p>${esc(p)}</p>`).join("")}
      </div>
    `;
    container.append(pageSheet);
    pageNum++;
  });

  // Attach click listeners to editable content blocks to update active section in AI Copilot
  attachSectionFocusListeners();
}

function createA4Sheet({ showHeader = true, headerLeft = "", footerLeft = "", footerCenter = "1", footerRight = "", isFront = false }) {
  const sheet = document.createElement("div");
  sheet.className = "a4-sheet";
  sheet.innerHTML = `
    ${showHeader ? `<div class="sheet-header"><span>${esc(headerLeft)}</span><span>PBL Academic Report</span></div>` : `<div></div>`}
    <div class="sheet-body" contenteditable="true" spellcheck="false"></div>
    <div class="sheet-footer">
      <span>${esc(footerLeft)}</span>
      <span class="sheet-pg-center">${esc(footerCenter)}</span>
      <span>${esc(footerRight)}</span>
    </div>
  `;
  return sheet;
}

function attachSectionFocusListeners() {
  $$(".editable-content-block").forEach(block => {
    block.onfocus = () => {
      const sec = block.dataset.section;
      setActiveSection(sec);
    };
    block.onmouseup = () => {
      checkTextSelection();
    };
    block.onkeyup = () => {
      $("#saveStatus").textContent = "● Unsaved edits";
      $("#saveStatus").style.color = "var(--danger)";
    };
  });
}

function setActiveSection(secName) {
  state.activeSection = secName;
  $("#copilotActiveSec").textContent = `Target: ${secName}`;
  $$(".outline-item").forEach(el => {
    if (el.textContent === secName) el.classList.add("active");
    else el.classList.remove("active");
  });
}

function scrollToSection(secName) {
  setActiveSection(secName);
  const targetId = `sec-${secName.replace(/[^a-zA-Z0-9]/g, "-")}`;
  const el = document.getElementById(targetId);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function checkTextSelection() {
  const sel = window.getSelection();
  const txt = sel.toString().trim();
  if (txt) {
    $("#selectionStatus").textContent = `Selected: "${txt.slice(0, 24)}…"`;
  } else {
    $("#selectionStatus").textContent = "No text selected";
  }
}

function initToolbar() {
  $$(".tool-btn[data-cmd]").forEach(btn => {
    btn.onclick = () => {
      const cmd = btn.dataset.cmd;
      document.execCommand(cmd, false, null);
      btn.classList.toggle("active", document.queryCommandState(cmd));
    };
  });

  $("#headingSelect").onchange = e => {
    const val = e.target.value;
    document.execCommand("formatBlock", false, `<${val}>`);
  };

  $("#fontSizeSelect").onchange = e => {
    const val = e.target.value;
    document.execCommand("fontSize", false, "3"); // base size
  };

  $("#insertTableBtn").onclick = () => {
    const htmlTable = `
      <table>
        <thead><tr><th>Parameter / Test ID</th><th>Specification / Input</th><th>Expected Output</th><th>Status</th></tr></thead>
        <tbody>
          <tr><td>TC-01</td><td>Ambient Temperature >= 38 C</td><td>Curtain motor engages to close</td><td>PASS</td></tr>
          <tr><td>TC-02</td><td>Ambient Temperature < 30 C</td><td>Curtain motor engages to open</td><td>PASS</td></tr>
        </tbody>
      </table>
      <p></p>
    `;
    document.execCommand("insertHTML", false, htmlTable);
  };
}

/* ═══════════════════════════════════════════════════════════════════════════
   ── AI COPILOT CHAT & EDITING ──
   ═══════════════════════════════════════════════════════════════════════════ */

async function sendCopilotMessage() {
  const input = $("#copilotInput");
  const msg = input.value.trim();
  if (!msg) return;
  input.value = "";

  const secName = state.activeSection || "Abstract";
  const sel = window.getSelection().toString().trim();

  // Find current text in the active section
  const activeBlock = document.querySelector(`.editable-content-block[data-section="${secName}"]`);
  const currentContent = activeBlock ? activeBlock.innerText : "";

  // Render user chat bubble
  renderCopilotBubble("user", msg);

  // Render loading assistant bubble
  const loadEl = renderCopilotBubble("bot", "Thinking and refining text…");

  try {
    const res = await fetch(`${API}/chat-edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        report_id: state.reportId,
        message: msg,
        section_name: secName,
        selected_text: sel,
        current_content: currentContent,
      }),
    });
    const d = await res.json();
    loadEl.remove();

    renderCopilotBubble("bot", d.reply, d.updated_content, d.target_section);

    // If updated content was returned, apply to the document canvas
    if (d.updated_content && d.target_section) {
      applyAiUpdateToCanvas(d.target_section, d.updated_content);
    }
  } catch (err) {
    loadEl.remove();
    renderCopilotBubble("bot", `Error communicating with AI: ${err.message}`);
  }
}

function renderCopilotBubble(sender, text, updatedContent = null, targetSection = null) {
  const container = $("#copilotMessages");
  const div = document.createElement("div");
  div.className = `copilot-msg ${sender}`;
  if (sender === "user") {
    div.innerHTML = `<div>${esc(text)}</div>`;
  } else {
    div.innerHTML = `
      <span class="avatar">AI</span>
      <div>
        <p>${esc(text)}</p>
        ${updatedContent ? `<button class="chip-btn" style="margin-top:8px;background:var(--lime);color:#000;font-weight:bold;" onclick="applyAiUpdateToCanvas('${attr(targetSection)}', \`${attr(updatedContent)}\`)">✓ Apply to ${esc(targetSection)}</button>` : ""}
      </div>
    `;
  }
  container.append(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

window.applyAiUpdateToCanvas = function(secName, newText) {
  const block = document.querySelector(`.editable-content-block[data-section="${secName}"]`);
  if (block) {
    block.innerHTML = newText.split("\n\n").map(p => `<p>${esc(p)}</p>`).join("");
    scrollToSection(secName);
    $("#saveStatus").textContent = "● Unsaved edits";
    $("#saveStatus").style.color = "var(--danger)";
    if (state.reportData && state.reportData.ai_content) {
      state.reportData.ai_content[secName] = newText;
    }
  }
};

async function saveDocument() {
  if (!state.reportId) return;
  const btn = $("#saveDocBtn");
  btn.disabled = true;
  btn.textContent = "Saving…";

  // Collect all section text from editable canvas blocks
  const updatedAiContent = {};
  $$(".editable-content-block").forEach(block => {
    const sec = block.dataset.section;
    if (sec) {
      updatedAiContent[sec] = block.innerText.trim();
    }
  });

  try {
    const res = await fetch(`${API}/save-report/${state.reportId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ai_content: updatedAiContent,
      }),
    });
    const d = await res.json();
    $("#saveStatus").textContent = "✓ All changes saved to DOCX";
    $("#saveStatus").style.color = "var(--lime)";
  } catch (err) {
    $("#saveStatus").textContent = "Save failed: " + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Save Changes";
  }
}

function downloadFile(type) {
  if (!state.reportId) return alert("Please generate a report first.");
  window.open(`${API}/download-${type}/${state.reportId}`, "_blank");
}

function loading(x) {
  const e = document.createElement("div");
  e.id = "loading";
  e.className = "loading";
  e.textContent = x;
  messages.append(e);
  bottom();
}
function removeLoad() { $("#loading")?.remove(); }
function progress(done) {
  const a = ["Reference format", "Team", "Faculty", "Project briefing", "Evidence", "Review"],
        n = done ? 6 : ["reference", "studentName", "studentRoll", "guide", "hod", "principal", "title", "group", "chat", "briefing", "technology", "results", "review"].indexOf(state.stage);
  $("#progress").innerHTML = a.map((x, i) => `<div class="${i <= Math.max(0, n) ? "complete" : ""}"><i></i>${x}</div>`).join("");
}
function bottom() { requestAnimationFrame(() => messages.scrollTo({ top: messages.scrollHeight, behavior: "smooth" })); }
function esc(x = "") { const e = document.createElement("div"); e.textContent = x; return e.innerHTML; }
function attr(x = "") { return esc(x).replace(/"/g, "&quot;"); }

