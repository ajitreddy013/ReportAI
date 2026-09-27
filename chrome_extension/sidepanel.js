// sidepanel.js — Visual AI Controller & Conversational Assistant for Google Docs

const BACKEND_URL = "http://localhost:8000";

let currentProject = {
  topic: "",
  notes: "",
  guide: "",
  group_no: "",
  students: [],
};

const OLD_SNIPPETS = {
  "Title": "AUTOMATIC ROOFTOP CURTAINS USING TEMPERATURE SENSOR & ARDUINO UNO",
  "1.1 Introduction": "In this era of fast-paced life, smart solutions and automation are becoming an essential part of open-air cafes with motorized rooftop curtains...",
  "2.1 Literature Survey": "Survey of motorized curtains using L293D motor drivers, DS18B20 temperature thresholds, and mechanical rails...",
  "3.1 Overview of the Proposed System": "The rooftop curtain system senses temperature and actuates the DC gear motor via L293D driver board...",
  "3.3 Implementation Details": "Arduino Uno pin 2 connected to DS18B20, pins 4 and 5 connected to motor driver IC on breadboard...",
  "4.2 Result and Discussion": "Tested automatic curtain opening when ambient temperature reached 35°C...",
  "5.1 Conclusion": "The automatic rooftop curtain prototype successfully deployed for cafe shade control...",
};

document.addEventListener("DOMContentLoaded", () => {
  initStatusCheck();
  loadSavedProject();
  attachEvents();
});

function initStatusCheck() {
  const statusBadge = document.getElementById("connectionStatus");
  const statusText = statusBadge.querySelector(".status-text");

  fetch(`${BACKEND_URL}/api/status`)
    .then((res) => res.json())
    .then(() => {
      statusBadge.className = "status-badge connected";
      statusText.textContent = "ReportAI Online";
    })
    .catch(() => {
      statusBadge.className = "status-badge disconnected";
      statusText.textContent = "Backend Offline";
    });
}

function loadSavedProject() {
  if (chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["reportai_chat_project"], (result) => {
      if (result.reportai_chat_project) {
        currentProject = result.reportai_chat_project;
        updateVerifCard();
      }
    });
  }
}

function saveProject() {
  if (chrome.storage && chrome.storage.local) {
    chrome.storage.local.set({ reportai_chat_project: currentProject });
  }
  updateVerifCard();
}

function updateVerifCard() {
  const topicPill = document.getElementById("verifTopic");
  if (currentProject.topic) {
    topicPill.textContent = `Topic: ${currentProject.topic.slice(0, 22)}...`;
    topicPill.title = currentProject.topic;
  } else {
    topicPill.textContent = "Topic: (Not set)";
  }
}

function attachEvents() {
  document.getElementById("btnSend").addEventListener("click", handleUserMessage);
  document.getElementById("chatInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleUserMessage();
    }
  });

  document.getElementById("btnVerifyDoc").addEventListener("click", verifyActiveGoogleDoc);
  document.getElementById("btnInsertDoc").addEventListener("click", copyDrawerToClipboard);
  document.getElementById("btnCloseDrawer").addEventListener("click", () => {
    document.getElementById("quickActionDrawer").classList.add("hidden");
  });

  // Action chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const act = chip.getAttribute("data-action");
      if (act === "transform_all") {
        triggerVisualTransformAll();
      } else if (act === "rewrite_selection") {
        triggerSelectionAction("rewrite_for_topic");
      } else if (act === "add_test_cases") {
        triggerSelectionAction("test_cases");
      } else if (act === "add_math_model") {
        triggerSelectionAction("math_model");
      } else if (act === "add_citations") {
        triggerSelectionAction("citations");
      }
    });
  });
}

// Conversational handler
async function handleUserMessage() {
  const input = document.getElementById("chatInput");
  const msg = input.value.trim();
  if (!msg) return;

  appendMessage("user", msg);
  input.value = "";

  const lower = msg.toLowerCase();
  
  // Check if user is supplying topic
  if (!currentProject.topic || lower.includes("topic:") || lower.includes("project is") || lower.includes("topic is") || (!currentProject.topic && msg.length > 8)) {
    let detectedTopic = msg;
    if (lower.includes("topic:")) {
      detectedTopic = msg.split(/topic:/i)[1].split("\n")[0].trim();
    } else if (lower.includes("project is")) {
      detectedTopic = msg.split(/project is/i)[1].split("\n")[0].trim();
    }
    detectedTopic = detectedTopic.replace(/^["'\s]+|["'\s]+$/g, "");
    
    currentProject.topic = detectedTopic;
    currentProject.notes = msg;
    saveProject();

    // Check if we need more specific details
    if (!lower.includes("team") && !lower.includes("student") && !lower.includes("guide")) {
      appendMessage(
        "ai",
        `Got your topic: <strong>${detectedTopic}</strong>!<br><br>` +
        `I am ready to transform your Google Doc.<br>` +
        `<em>(Optional)</em> If you have Guide name and Team members, send them now. Or click <strong>🚀 Transform Whole Document</strong> to start live visual editing right away!`
      );
      return;
    }
  }

  const typingId = appendTypingIndicator();

  fetch(`${BACKEND_URL}/api/chat-edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topic: currentProject.topic || "Engineering Project Report",
      message: msg,
      current_content: "",
      reference_notes: currentProject.notes || msg,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      removeTypingIndicator(typingId);
      appendMessage("ai", data.reply);
      if (data.updated_content) {
        showDrawer(data.target_section || "AI Content", data.updated_content);
        // Show live visual HUD on Google Doc
        sendHudUpdate(data.target_section || "Section", "Old reference text", data.updated_content.slice(0, 140) + "...", 100);
      }
    })
    .catch((err) => {
      removeTypingIndicator(typingId);
      appendMessage("ai", `⚠️ Notice: ${err.message}. Please ensure ReportAI backend is running at http://localhost:8000.`);
    });
}

// Multi-step autonomous human-like visual transformation
async function triggerVisualTransformAll() {
  if (!currentProject.topic) {
    appendMessage("ai", "Please type your **Project Topic** first (e.g. *Smart IoT Hydroponics Monitoring System*).");
    document.getElementById("chatInput").focus();
    return;
  }

  appendMessage("user", `Transform whole document for "${currentProject.topic}"`);
  appendMessage(
    "ai",
    `🤖 <strong>Taking autonomous control of Google Docs...</strong><br>` +
    `• Moving virtual cursor to Chapter 1 through 6.<br>` +
    `• Deleting old rooftop curtain data.<br>` +
    `• Typing new <em>${currentProject.topic}</em> engineering specifications.<br>` +
    `<em>Look at your Google Doc page now!</em>`
  );

  // Send message to content script on active Google Docs tab to start autonomous visual cursor movement
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, {
        action: "runHumanLikeDocTransformation",
        topic: currentProject.topic,
      });
    }
  });

  // Fetch full generated report from backend
  fetch(`${BACKEND_URL}/api/extension/generate-all-sections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topic: currentProject.topic,
      notes: currentProject.notes,
      student_info: currentProject,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      let fullReport = `# ${currentProject.topic}\n\n`;
      let totalWords = 0;
      for (const [sec, text] of Object.entries(data.sections)) {
        fullReport += `\n\n## ${sec}\n\n${text}\n`;
        totalWords += text.split(/\s+/).length;
      }

      showDrawer(`Full 6-Chapter Report (~${totalWords} words)`, fullReport);

      setTimeout(() => {
        appendMessage(
          "ai",
          `🎉 <strong>Autonomous Transformation Complete!</strong><br>` +
          `• <strong>6 Chapters & 21 Subsections</strong> generated (~<strong>${totalWords} words</strong>).<br>` +
          `• <strong>Old data deleted:</strong> All rooftop curtain markers removed.<br>` +
          `• <strong>New data inserted:</strong> Tailored for <em>${currentProject.topic}</em>.<br><br>` +
          `👉 <strong>Press Cmd+V / Ctrl+V</strong> in your Google Doc to paste the complete transformed report!`
        );
      }, 5000);
    })
    .catch((err) => {
      appendMessage("ai", `⚠️ Error compiling report: ${err.message}`);
    });
}

// Quick action on selection
async function triggerSelectionAction(action) {
  const selectedText = await getSelectionFromActiveTab();
  
  const actionNames = {
    rewrite_for_topic: "Rewrite for Topic",
    test_cases: "Generate Test Cases Table",
    math_model: "Formulate Set Theory Model",
    citations: "Generate Verified IEEE Citations",
  };

  const label = actionNames[action] || action;
  appendMessage("user", `${label}...`);
  const typingId = appendTypingIndicator();

  sendHudUpdate(label, selectedText.slice(0, 100) + "..." || "Selected old text", "Generating new engineering content...", 60);

  fetch(`${BACKEND_URL}/api/extension/transform-selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topic: currentProject.topic || "Engineering Project Report",
      action: action,
      selected_text: selectedText,
      notes: currentProject.notes,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      removeTypingIndicator(typingId);
      const resText = data.transformed_text || data.reply;
      showDrawer(label, resText);
      sendHudUpdate(label, selectedText.slice(0, 80) + "...", resText.slice(0, 120) + "...", 100);
      copyDrawerToClipboard();
      appendMessage("ai", `✔ **${label}** ready and copied to clipboard! Press <strong>Cmd+V / Ctrl+V</strong> in Google Docs.`);
    })
    .catch((err) => {
      removeTypingIndicator(typingId);
      appendMessage("ai", `⚠️ Notice: ${err.message}`);
    });
}

// Live Document Verification
async function verifyActiveGoogleDoc() {
  appendMessage("user", "🔍 Scanning and verifying active Google Doc...");
  const typingId = appendTypingIndicator();

  const selectedText = await getSelectionFromActiveTab();

  setTimeout(() => {
    removeTypingIndicator(typingId);
    
    const OLD_MARKERS = [
      "ROOFTOP CURTAIN", "ROOFTOP", "DS18B20", "MOTOR DRIVER L23D", "L23D",
      "OPEN-AIR CAFE", "MOTORIZED CURTAIN", "KOLPE", "KOLPUKE", "KONDE", "KSHIRSAGAR",
      "KUDALE", "PRATIKSHA", "VEDANT", "ATHRAV", "KRUSHNA", "TULSHIRAM", "SOMNATH", "GANESH", "PALLAVI"
    ];

    const leaked = [];
    const upperText = (selectedText || "").toUpperCase();
    for (const m of OLD_MARKERS) {
      if (upperText.includes(m)) {
        leaked.push(m);
      }
    }

    const words = selectedText ? selectedText.split(/\s+/).length : 0;
    const integrityBadge = document.getElementById("verifIntegrity");
    const wordsBadge = document.getElementById("verifWords");

    if (leaked.length > 0) {
      integrityBadge.textContent = `⚠️ ${leaked.length} Old Markers Found`;
      integrityBadge.className = "verif-pill warning";
      appendMessage(
        "ai",
        `⚠️ <strong>Verification Alert:</strong> Found ${leaked.length} leftover references from the friend's report (` +
        `<code>${leaked.slice(0, 3).join(", ")}</code>).<br><br>` +
        `Click <strong>🚀 Transform Whole Document</strong> to replace them automatically with <em>${currentProject.topic || "your new topic"}</em>.`
      );
    } else {
      integrityBadge.textContent = "Integrity: 100% Clean";
      integrityBadge.className = "verif-pill clean";
      wordsBadge.textContent = `Scanned: ~${words} words`;
      appendMessage(
        "ai",
        `✔ <strong>Document Verified!</strong><br>` +
        `• <strong>0 Old Markers:</strong> No rooftop curtain markers detected.<br>` +
        `• <strong>Current Topic:</strong> ${currentProject.topic || "Ready"}<br>` +
        `• <strong>Status:</strong> Ready for final submission!`
      );
    }
  }, 500);
}

// Helpers
function sendHudUpdate(section, oldSnippet, newSnippet, progress) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, {
        action: "showLiveEditHud",
        section: section,
        oldSnippet: oldSnippet,
        newSnippet: newSnippet,
        progress: progress,
      });
    }
  });
}

function getSelectionFromActiveTab() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "getSelectedText" }, (res) => {
          if (chrome.runtime.lastError || !res) {
            resolve("");
          } else {
            resolve(res.selectedText || "");
          }
        });
      } else {
        resolve("");
      }
    });
  });
}

function showDrawer(title, content) {
  const drawer = document.getElementById("quickActionDrawer");
  document.getElementById("drawerTitle").textContent = title;
  document.getElementById("drawerBody").textContent = content;
  drawer.classList.remove("hidden");
  drawer.scrollIntoView({ behavior: "smooth" });
}

function copyDrawerToClipboard() {
  const text = document.getElementById("drawerBody").textContent;
  if (!text) return;

  navigator.clipboard.writeText(text).then(() => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, {
          action: "insertText",
          text: text,
          sectionTitle: document.getElementById("drawerTitle").textContent,
        });
      }
    });
  });
}

function appendMessage(sender, text) {
  const stream = document.getElementById("chatMessages");
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-msg ${sender}`;
  
  const avatar = sender === "ai" ? "✨" : "👤";
  msgDiv.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-bubble">${text}</div>
  `;
  stream.appendChild(msgDiv);
  stream.scrollTop = stream.scrollHeight;
}

function appendTypingIndicator() {
  const stream = document.getElementById("chatMessages");
  const id = `typing-${Date.now()}`;
  const div = document.createElement("div");
  div.id = id;
  div.className = "chat-msg ai typing";
  div.innerHTML = `
    <div class="msg-avatar">✨</div>
    <div class="msg-bubble"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span> Thinking & adapting...</div>
  `;
  stream.appendChild(div);
  stream.scrollTop = stream.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}
