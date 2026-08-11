function formatTimestamp(seconds) {
  if (typeof seconds !== 'number' || isNaN(seconds)) {
    return '00:00.000';
  }
  const totalMs = Math.round(seconds * 1000);
  const hrs = Math.floor(totalMs / 3600000);
  const mins = Math.floor((totalMs % 3600000) / 60000);
  const secs = Math.floor((totalMs % 60000) / 1000);
  const ms = totalMs % 1000;

  const pad = (num, size) => num.toString().padStart(size, '0');

  if (hrs > 0) {
    return `${pad(hrs, 2)}:${pad(mins, 2)}:${pad(secs, 2)}.${pad(ms, 3)}`;
  }
  return `${pad(mins, 2)}:${pad(secs, 2)}.${pad(ms, 3)}`;
}

function formatTranscript(history) {
  if (!Array.isArray(history) || history.length === 0) {
    return '';
  }
  return history.map((item) => {
    if (typeof item === 'string') {
      return item;
    }
    const text = item.text || '';
    if (item.start !== undefined && item.start !== null && item.end !== undefined && item.end !== null) {
      return `[${formatTimestamp(item.start)} --> ${formatTimestamp(item.end)}] ${text}`;
    }
    return text;
  }).join('\n');
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    const languageSelect = document.getElementById('languageSelect');

    const fontSizeSelect = document.getElementById('fontSizeSelect');
    const translateCheckbox = document.getElementById('translateCheckbox');
    const serverUrlInput = document.getElementById('serverUrl');

    const toggleBtn = document.getElementById('toggleBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const statusDiv = document.getElementById('status');

  // Listen for unexpected capture stopped / disconnect events
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'captureStopped') {
      updateUI(false);
      statusDiv.textContent = message.error ? `Status: Stopped (${message.error})` : 'Status: Disconnected';
    }
  });


  // Load saved server URL
  chrome.storage.local.get(['serverUrl'], (result) => {
    if (result.serverUrl && serverUrlInput) {
      serverUrlInput.value = result.serverUrl;
    }
  });

  // Request state from background service worker
  chrome.runtime.sendMessage({ action: 'getStatus' }, (response) => {
    if (chrome.runtime.lastError) {
      statusDiv.textContent = 'Status: Ready';
      return;
    }
    if (response) {
      if (response.language) {
        languageSelect.value = response.language;
      }
      if (response.fontSize) {
        fontSizeSelect.value = response.fontSize.toString();
      }
      if (response.task) {
        translateCheckbox.checked = (response.task === 'translate');
      }
      updateUI(response.isCapturing);
    }
  });

  function sendConfigUpdate() {
    const selectedFontSize = parseInt(fontSizeSelect.value, 10);
    const selectedLanguage = languageSelect.value;
    const selectedTask = translateCheckbox.checked ? 'translate' : 'transcribe';
    chrome.runtime.sendMessage({
      action: 'updateConfig',
      fontSize: selectedFontSize,
      language: selectedLanguage,
      task: selectedTask
    });
  }

  // Handle dynamic font size or translation toggle changes
  fontSizeSelect.addEventListener('change', sendConfigUpdate);
  translateCheckbox.addEventListener('change', sendConfigUpdate);

  function updateUI(isCapturing) {
    if (isCapturing) {
      toggleBtn.textContent = 'Stop Captioning';
      toggleBtn.classList.add('active');
      statusDiv.textContent = 'Status: Captioning...';
      statusDiv.classList.add('connected');
      languageSelect.disabled = true;
    } else {
      toggleBtn.textContent = 'Start Captioning';
      toggleBtn.classList.remove('active');
      statusDiv.textContent = 'Status: Idle';
      statusDiv.classList.remove('connected');
      languageSelect.disabled = false;
    }
  }

  toggleBtn.addEventListener('click', async () => {
    const isCurrentlyActive = toggleBtn.classList.contains('active');
    const selectedLanguage = languageSelect.value;
    const selectedFontSize = parseInt(fontSizeSelect.value, 10);
    const selectedTask = translateCheckbox.checked ? 'translate' : 'transcribe';
    const serverUrl = serverUrlInput ? serverUrlInput.value.trim() : '';
    
    // Save to storage
    if (serverUrlInput) {
      chrome.storage.local.set({ serverUrl: serverUrl });
    }

    if (!isCurrentlyActive) {
      if (!serverUrl.startsWith('ws://') && !serverUrl.startsWith('wss://')) {
        statusDiv.textContent = 'Status: Error - URL must start with ws:// or wss://';
        return;
      }

      // Query active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab) {
        statusDiv.textContent = 'Status: Error - No active tab';
        return;
      }

      chrome.runtime.sendMessage(
        { action: 'start', language: selectedLanguage, fontSize: selectedFontSize, task: selectedTask, serverUrl: serverUrl, tabId: tab.id },
        (response) => {
          if (chrome.runtime.lastError) {
            statusDiv.textContent = 'Status: Error starting';
            console.error(chrome.runtime.lastError);
            return;
          }
          if (response && response.success) {
            updateUI(true);
          } else {
            statusDiv.textContent = 'Status: Failed to start (' + (response.error || 'Unknown') + ')';
          }
        }
      );
    } else {
      chrome.runtime.sendMessage({ action: 'stop' }, (response) => {
        if (chrome.runtime.lastError) {
          console.error(chrome.runtime.lastError);
        }
        updateUI(false);
      });
    }
  });

  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      chrome.runtime.sendMessage({ action: 'getTranscriptHistory' }, (response) => {
        if (chrome.runtime.lastError) {
          console.error(chrome.runtime.lastError);
          return;
        }
        const history = response?.transcriptHistory || [];
        if (history.length === 0) {
          return;
        }
        const formattedText = formatTranscript(history);
        const blob = new Blob([formattedText], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'transcript.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
    });
  }
  });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { formatTimestamp, formatTranscript };
}
