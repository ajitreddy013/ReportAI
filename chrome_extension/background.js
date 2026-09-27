// background.js — Service worker for ReportAI Chrome Extension

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error("Error setting panel behavior:", error));

chrome.runtime.onInstalled.addListener(() => {
  console.log("ReportAI Google Docs Copilot Extension Installed.");
});
