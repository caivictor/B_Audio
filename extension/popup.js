document.addEventListener('DOMContentLoaded', () => {
  const languageSelect = document.getElementById('languageSelect');
  const toggleBtn = document.getElementById('toggleBtn');
  const statusDiv = document.getElementById('status');

  // Listen for unexpected capture stopped / disconnect events
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'captureStopped') {
      updateUI(false);
      statusDiv.textContent = message.error ? `Status: Stopped (${message.error})` : 'Status: Disconnected';
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
      updateUI(response.isCapturing);
    }
  });

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

    if (!isCurrentlyActive) {
      // Query active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab) {
        statusDiv.textContent = 'Status: Error - No active tab';
        return;
      }

      chrome.runtime.sendMessage(
        { action: 'start', language: selectedLanguage, tabId: tab.id },
        (response) => {
          if (chrome.runtime.lastError) {
            statusDiv.textContent = 'Status: Error starting';
            console.error(chrome.runtime.lastError);
            return;
          }
          if (response && response.success) {
            updateUI(true);
          } else {
            statusDiv.textContent = 'Status: Failed to start';
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
