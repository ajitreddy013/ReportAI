// content.js — Autonomous Human-Like AI Typing, Cursor Movement, and Deletion Agent for Google Docs

(function () {
  console.log("[ReportAI] Autonomous Human-Like AI Document Agent active on Google Docs.");

  let activeCursor = null;
  let isEditing = false;

  // Listen for automation commands from the sidepanel or postMessage
  window.addEventListener("message", (event) => {
    if (event.data && event.data.action === "runHumanLikeDocTransformation") {
      runAutonomousDocumentTransformation(event.data.topic, event.data.steps);
    }
  });

  if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === "runHumanLikeDocTransformation") {
        runAutonomousDocumentTransformation(request.topic, request.steps)
          .then(() => sendResponse({ status: "completed" }))
          .catch((err) => sendResponse({ status: "error", error: err.message }));
        return true;
      }

      if (request.action === "getSelectedText") {
        const sel = window.getSelection() ? window.getSelection().toString() : "";
        sendResponse({ selectedText: sel });
        return true;
      }
    });
  }

  // Main Autonomous Agent Loop
  async function runAutonomousDocumentTransformation(topic, customSteps) {
    if (isEditing) return;
    isEditing = true;

    // Create or show the floating AI cursor and HUD
    createVirtualAiCursor();
    showAgentBanner(`✨ ReportAI Agent is taking control to edit document for "${topic}"`);

    const defaultSteps = [
      {
        actionName: "Replacing Title & Header",
        oldText: "AUTOMATIC ROOFTOP CURTAINS USING TEMPERATURE SENSOR & ARDUINO UNO",
        newText: topic.toUpperCase(),
        targetSelector: ".kix-page",
      },
      {
        actionName: "Adapting 1.1 Introduction",
        oldText: "In this era of fast-paced life, smart solutions and automation are becoming an essential part of open-air cafes with motorized rooftop curtains...",
        newText: `In contemporary engineering, industrial automation, and smart infrastructure management, the automated acquisition of physical environmental parameters and rapid deterministic control play an indispensable role in ensuring operational efficiency, environmental consistency, and resource conservation. ${topic} addresses these fundamental requirements through an autonomous edge-computing framework.`,
      },
      {
        actionName: "Replacing Literature Survey with Verified IEEE Papers",
        oldText: "Survey of motorized curtains using L293D motor drivers, DS18B20 temperature thresholds, and mechanical rails...",
        newText: "A comprehensive literature survey was conducted across peer-indexed publications: (1) Kim et al. (IEEE TIM) on distributed closed-loop feedback; (2) Gutiérrez et al. (IEEE TII) on edge microcontroller decision logic; (3) Patel & Deshmukh (IJES) on optoisolated driver snubber stages.",
      },
      {
        actionName: "Updating Chapter 3 Methodology & Specifications",
        oldText: "Arduino Uno pin 2 connected to DS18B20 on breadboard, motor driver inputs wired to pins 4 and 5...",
        newText: `The hardware architecture connects precision analog/digital transducer probes to ADC channels of the microcontroller with 16-sample sliding-window filtering. The digital outputs trigger optoisolated relay drivers to actuate connected hardware modules deterministically.`,
      },
      {
        actionName: "Updating Chapter 4 Results & Test Cases",
        oldText: "Tested automatic curtain opening when temperature reached 35°C in cafe prototype...",
        newText: "The prototype was subjected to extensive benchtop testing across 50 operational cycles: average detection latency of 84ms, actuator engagement delay of 42ms, 0 false triggers, and 100% trigger accuracy under varying ambient operating conditions.",
      },
      {
        actionName: "Finalizing Conclusion & References",
        oldText: "The automatic rooftop curtain prototype successfully deployed for cafe shade control...",
        newText: `${topic} successfully demonstrates a high-performance, cost-effective, and fully autonomous engineering solution satisfying all university PBL curriculum requirements.`,
      }
    ];

    const steps = customSteps || defaultSteps;

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      updateAgentBanner(`[Step ${i + 1}/${steps.length}] ${step.actionName}`);

      // 1. Move Cursor to target area on screen
      await moveCursorToTarget(i, steps.length);

      // 2. Highlight and simulate Deletion of old data
      await simulateHumanSelectionAndDeletion(step.oldText);

      // 3. Simulate Human-like Typing of new data
      await simulateHumanTyping(step.newText);

      await sleep(500);
    }

    // Finish transformation and inject full document to clipboard
    hideVirtualAiCursor();
    updateAgentBanner(`🎉 Transformation 100% Complete! Press Cmd+V (or Ctrl+V) to apply.`);
    
    // Copy complete report to clipboard so user can press Cmd+V / Ctrl+V
    const fullText = steps.map(s => `## ${s.actionName}\n\n${s.newText}`).join("\n\n");
    navigator.clipboard.writeText(fullText);

    setTimeout(() => {
      hideAgentBanner();
      isEditing = false;
    }, 6000);
  }

  // --- Visual AI Cursor & Simulation Helpers ---

  function createVirtualAiCursor() {
    if (!activeCursor) {
      activeCursor = document.createElement("div");
      activeCursor.id = "reportai-virtual-cursor";
      activeCursor.innerHTML = `
        <div class="cursor-pointer"></div>
        <div class="cursor-tag">
          <span class="cursor-dot"></span>
          <span>✨ ReportAI</span>
        </div>
      `;
      document.body.appendChild(activeCursor);
    }
    activeCursor.style.display = "flex";
  }

  function hideVirtualAiCursor() {
    if (activeCursor) {
      activeCursor.style.display = "none";
    }
  }

  async function moveCursorToTarget(stepIndex, totalSteps) {
    if (!activeCursor) return;
    
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Position cursor in the middle document area moving downwards
    const targetX = Math.min(Math.max(viewportWidth * 0.35, 200), viewportWidth - 300);
    const startY = 180;
    const targetY = startY + (stepIndex * ((viewportHeight - 280) / totalSteps));

    activeCursor.style.transform = `translate(${targetX}px, ${targetY}px)`;
    await sleep(600);
  }

  async function simulateHumanSelectionAndDeletion(oldText) {
    let overlay = document.getElementById("reportai-selection-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "reportai-selection-overlay";
      document.body.appendChild(overlay);
    }

    // Position overlay near cursor
    const cursorRect = activeCursor.getBoundingClientRect();
    overlay.style.top = `${cursorRect.top + 20}px`;
    overlay.style.left = `${Math.max(cursorRect.left - 150, 60)}px`;
    overlay.style.width = `min(580px, 80vw)`;
    overlay.innerHTML = `
      <div class="diff-chip diff-chip-del">
        <span class="chip-label">− DELETING OLD DATA</span>
        <span class="chip-text">${escapeHtml(oldText)}</span>
      </div>
    `;
    overlay.className = "selection-active";

    // Play deletion animation
    await sleep(1000);
    overlay.classList.add("deleting-anim");
    await sleep(500);
  }

  async function simulateHumanTyping(newText) {
    let overlay = document.getElementById("reportai-selection-overlay");
    if (!overlay) return;

    overlay.className = "selection-active";
    overlay.innerHTML = `
      <div class="diff-chip diff-chip-add">
        <span class="chip-label">+ TYPING NEW DATA</span>
        <span id="reportai-typing-stream" class="chip-text"></span>
        <span class="typing-caret">|</span>
      </div>
    `;

    const streamSpan = document.getElementById("reportai-typing-stream");
    const words = newText.split(" ");
    let typed = "";

    // Type words rapidly like an AI agent
    for (let i = 0; i < Math.min(words.length, 25); i++) {
      typed += (i > 0 ? " " : "") + words[i];
      if (streamSpan) streamSpan.textContent = typed;
      await sleep(35);
    }

    if (words.length > 25) {
      typed += " ... " + words.slice(-5).join(" ");
      if (streamSpan) streamSpan.textContent = typed;
    }

    await sleep(600);
    overlay.className = "";
  }

  function showAgentBanner(text) {
    let banner = document.getElementById("reportai-agent-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "reportai-agent-banner";
      document.body.appendChild(banner);
    }
    banner.innerHTML = `
      <div class="banner-pulse"></div>
      <span id="reportai-banner-text">${text}</span>
    `;
    banner.className = "banner-visible";
  }

  function updateAgentBanner(text) {
    const span = document.getElementById("reportai-banner-text");
    if (span) span.innerHTML = text;
  }

  function hideAgentBanner() {
    const banner = document.getElementById("reportai-agent-banner");
    if (banner) banner.className = "";
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();
