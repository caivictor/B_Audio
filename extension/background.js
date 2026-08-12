let isCapturing = false;
let currentLanguage = 'es';
let currentFontSize = 24;
let currentTask = 'transcribe';
let currentServerUrl = 'ws://192.168.0.30:8000/transcribe';
let currentTabId = null;
let transcriptHistory = [];

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'getStatus') {
    sendResponse({ isCapturing, language: currentLanguage, fontSize: currentFontSize, task: currentTask, tabId: currentTabId, transcriptHistory });
    return true;
  }

  if (message.action === 'getTranscriptHistory' || message.action === 'getTranscript') {
    sendResponse({ transcriptHistory });
    return true;
  }

  if (message.action === 'updateConfig') {
    if (message.fontSize) currentFontSize = message.fontSize;
    if (message.language) currentLanguage = message.language;
    if (message.task) currentTask = message.task;
    chrome.runtime.sendMessage({
      action: 'updateConfig',
      fontSize: currentFontSize,
      language: currentLanguage,
      task: currentTask
    }).catch(() => {});
    sendResponse({ success: true });
    return true;
  }

  if (message.action === 'start') {
    currentLanguage = message.language || 'es';
    currentFontSize = message.fontSize || 24;
    currentTask = message.task || 'transcribe';
    currentServerUrl = message.serverUrl || 'ws://192.168.0.30:8000/transcribe';
    currentTabId = message.tabId;
    transcriptHistory = [];
    
    // Inject the content script into the active tab to render the UI
    chrome.scripting.executeScript({
      target: { tabId: currentTabId },
      files: ['content.js']
    }).catch(err => console.error("Failed to inject content script", err));

    chrome.tabCapture.getMediaStreamId({ targetTabId: currentTabId }, async (streamId) => {
      if (chrome.runtime.lastError || !streamId) {
        console.error('Failed to get media stream ID:', chrome.runtime.lastError);
        sendResponse({ success: false, error: chrome.runtime.lastError?.message });
        return;
      }

      try {
        const hasDoc = await chrome.offscreen.hasDocument();
        if (!hasDoc) {
          let resolveReady;
          const readyPromise = new Promise((resolve) => { resolveReady = resolve; });
          const readyListener = (msg) => {
            if (msg.action === 'offscreenReady') {
              chrome.runtime.onMessage.removeListener(readyListener);
              resolveReady();
            }
          };
          chrome.runtime.onMessage.addListener(readyListener);

          await chrome.offscreen.createDocument({
            url: 'offscreen.html',
            reasons: ['USER_MEDIA'],
            justification: 'Capture tab audio for real-time transcription'
          });

          await readyPromise;
        }

        chrome.runtime.sendMessage({
          action: 'startCapture',
          streamId,
          language: currentLanguage,
          fontSize: currentFontSize,
          task: currentTask,
          serverUrl: currentServerUrl
        });

        isCapturing = true;
        sendResponse({ success: true });
      } catch (err) {
        console.error('Error creating offscreen document:', err);
        sendResponse({ success: false, error: err.message });
      }
    });

    return true; // Keep sendResponse open for async handler
  }

  if (message.action === 'stop') {
    if (currentTabId !== null) {
      chrome.tabs.sendMessage(currentTabId, { action: 'hideCaption' }).catch(() => {});
    }
    isCapturing = false;
    currentTabId = null;
    chrome.runtime.sendMessage({ action: 'stopCapture' });

    chrome.offscreen.hasDocument().then((hasDoc) => {
      if (hasDoc) {
        chrome.offscreen.closeDocument().catch((err) => {
          console.error('Error closing offscreen document:', err);
        });
      }
    });

    sendResponse({ success: true });
    return true;
  }

  if (message.action === 'captureStopped') {
    if (currentTabId !== null) {
      chrome.tabs.sendMessage(currentTabId, { action: 'hideCaption' }).catch(() => {});
    }
    isCapturing = false;
    currentTabId = null;
    chrome.offscreen.hasDocument().then((hasDoc) => {
      if (hasDoc) {
        chrome.offscreen.closeDocument().catch((err) => {
          console.error('Error closing offscreen document:', err);
        });
      }
    });
    // Broadcast captureStopped to update popup UI
    chrome.runtime.sendMessage(message).catch(() => {});
  }

  // Relay transcription text to the content script in the active tab (ADV-012)
  if (message.action === 'captionText') {
    transcriptHistory.push({
      text: message.text,
      start: message.start !== undefined ? message.start : null,
      end: message.end !== undefined ? message.end : null
    });
    if (transcriptHistory.length > 1000) {
      transcriptHistory.shift();
    }
    if (currentTabId !== null) {
      if (chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(['fontFamily', 'textColor', 'strokeThickness'], (settings) => {
          chrome.tabs.sendMessage(currentTabId, {
            action: 'showCaption',
            text: message.text,
            fontSize: currentFontSize,
            fontFamily: settings.fontFamily,
            textColor: settings.textColor,
            strokeThickness: settings.strokeThickness
          }).catch(() => {}); // ignore errors if tab closed
        });
      } else {
        chrome.tabs.sendMessage(currentTabId, {
          action: 'showCaption',
          text: message.text,
          fontSize: currentFontSize
        }).catch(() => {}); // ignore errors if tab closed
      }
    }
    if (sendResponse) sendResponse({ success: true });
    return true;
  }
});

function cleanupCapture() {
  if (currentTabId !== null) {
    chrome.tabs.sendMessage(currentTabId, { action: 'hideCaption' }).catch(() => {});
  }
  isCapturing = false;
  currentTabId = null;
  chrome.runtime.sendMessage({ action: 'stopCapture' }).catch(() => {});
  chrome.offscreen.hasDocument().then((hasDoc) => {
    if (hasDoc) {
      chrome.offscreen.closeDocument().catch((err) => {
        console.error('Error closing offscreen document:', err);
      });
    }
  }).catch(() => {});
}

// Listen for tab removal (ADV-018)
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabId === currentTabId && isCapturing) {
    console.log(`Captured tab ${tabId} closed. Stopping capture.`);
    cleanupCapture();
    chrome.runtime.sendMessage({
      action: 'captureStopped',
      error: 'Tab was closed'
    }).catch(() => {});
  }
});

// Listen for tab updates/refreshes (ADV-018)
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (tabId === currentTabId && isCapturing && changeInfo.status === 'complete') {
    console.log(`Captured tab ${tabId} refreshed/navigated. Re-injecting content script.`);
    chrome.scripting.executeScript({
      target: { tabId: currentTabId },
      files: ['content.js']
    }).catch((err) => console.error("Failed to re-inject content script:", err));
  }
});
