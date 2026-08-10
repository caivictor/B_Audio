let ws = null;
let mediaStream = null;
let audioContext = null;
let processorNode = null;
let pcmBuffer = [];
let currentLanguage = 'es';
let currentFontSize = 24;
let currentTask = 'transcribe';
let isReconnecting = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 3;
const TARGET_SAMPLE_RATE = 16000;
const CHUNK_DURATION_SEC = 1.0;
const SAMPLES_PER_CHUNK = TARGET_SAMPLE_RATE * CHUNK_DURATION_SEC; // 16000 samples = 1 sec

// Notify background service worker that offscreen document is ready
chrome.runtime.sendMessage({ action: 'offscreenReady' });

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'startCapture') {
    startCapture(message.streamId, message.language, message.fontSize, message.task);
  } else if (message.action === 'stopCapture') {
    stopCapture();
  } else if (message.action === 'updateConfig') {
    if (message.language) currentLanguage = message.language;
    if (message.fontSize) currentFontSize = message.fontSize;
    if (message.task) currentTask = message.task;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'config',
        language: currentLanguage,
        fontSize: currentFontSize,
        task: currentTask
      }));
    }
  }
});

function handleWsDisconnect(errorMsg) {
  stopCapture();
  chrome.runtime.sendMessage({
    action: 'captureStopped',
    error: errorMsg || 'WebSocket connection lost'
  });
}

async function startCapture(streamId, language, fontSize, task) {
  stopCapture(); // Clean up any existing capture session
  currentLanguage = language || 'es';
  currentFontSize = fontSize || 24;
  currentTask = task || 'transcribe';

  try {
    // 1. Obtain MediaStream from Chrome tab capture streamId FIRST (DEF-007)
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      },
      video: false
    });
    
    // Listen for the native Chrome "Stop sharing" button
    if (mediaStream.getTracks().length > 0) {
      mediaStream.getTracks()[0].onended = () => {
        console.log("Media stream ended natively by user.");
        handleWsDisconnect("Native capture stopped");
      };
    }

    // 2. Connect WebSocket to local client only after media stream is acquired
    ws = new WebSocket('ws://localhost:8765');
    setupWebSocketHandlers();

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(mediaStream);

    // Route audio to destination so the user can still hear tab audio
    source.connect(audioContext.destination);

    // Create ScriptProcessorNode for processing raw PCM audio
    const bufferSize = 4096;
    processorNode = audioContext.createScriptProcessor(bufferSize, 1, 1);

    const inputSampleRate = audioContext.sampleRate;
    const ratio = inputSampleRate / TARGET_SAMPLE_RATE;

    processorNode.onaudioprocess = (e) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        return;
      }

      const inputData = e.inputBuffer.getChannelData(0); // Mono channel
      const outputLength = Math.floor(inputData.length / ratio);

      for (let i = 0; i < outputLength; i++) {
        const inputIdx = Math.floor(i * ratio);
        let sample = inputData[inputIdx];
        
        // Clamp sample to range [-1.0, 1.0]
        sample = Math.max(-1.0, Math.min(1.0, sample));
        
        // Convert to 16-bit PCM integer (-32768 to 32767)
        const int16Sample = sample < 0 ? sample * 32768 : sample * 32767;
        pcmBuffer.push(Math.round(int16Sample));

        // When buffer reaches ~1 second chunk, send to local client
        if (pcmBuffer.length >= SAMPLES_PER_CHUNK) {
          sendPcmChunk();
        }
      }
    };

    source.connect(processorNode);
    // Dummy connection required for ScriptProcessorNode in some browsers
    processorNode.connect(audioContext.destination);

  } catch (err) {
    console.error('Failed to start audio capture:', err);
    stopCapture();
    chrome.runtime.sendMessage({
      action: 'captureStopped',
      error: err.message || 'Failed to start audio capture'
    });
  }
}

function setupWebSocketHandlers() {
  if (!ws) return;

  ws.onopen = () => {
    console.log('WebSocket connected to local client.');
    reconnectAttempts = 0;
    isReconnecting = false;
    // Send initial config message
    const config = {
      type: 'config',
      language: currentLanguage,
      fontSize: currentFontSize,
      task: currentTask
    };
    ws.send(JSON.stringify(config));
  };

  ws.onerror = (err) => {
    console.error('WebSocket error:', err);
  };

  ws.onclose = () => {
    console.log('WebSocket connection closed.');
    if (mediaStream && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++;
      isReconnecting = true;
      console.log(`Attempting WebSocket reconnect ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}...`);
      setTimeout(() => {
        if (mediaStream) {
          ws = new WebSocket('ws://localhost:8765');
          setupWebSocketHandlers();
        }
      }, 1000);
    } else {
      handleWsDisconnect('WebSocket connection closed');
    }
  };
}

function sendPcmChunk() {
  if (pcmBuffer.length === 0 || !ws || ws.readyState !== WebSocket.OPEN) {
    return;
  }

  const int16Array = new Int16Array(pcmBuffer);
  ws.send(int16Array.buffer);
  pcmBuffer = [];
}

function stopCapture() {
  if (ws) {
    ws.onclose = null;
    ws.onerror = null;
    if (ws.readyState === WebSocket.OPEN) {
      sendPcmChunk();
      ws.close();
    }
    ws = null;
  }

  if (processorNode) {
    processorNode.disconnect();
    processorNode = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }

  pcmBuffer = [];
}
