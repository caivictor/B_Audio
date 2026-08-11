document.addEventListener('DOMContentLoaded', () => {
  const languageSelect = document.getElementById('languageSelect');

  const fontSizeSelect = document.getElementById('fontSizeSelect');
  const translateCheckbox = document.getElementById('translateCheckbox');
  const serverUrlInput = document.getElementById('serverUrl');

  const toggleBtn = document.getElementById('toggleBtn');
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
});
