// content.js - Injected into the active tab to display captions

if (!window.__webCaptionerInitialized) {
  window.__webCaptionerInitialized = true;
  
  const container = document.createElement('div');
  container.id = 'webcaptioner-overlay';
  Object.assign(container.style, {
    position: 'fixed',
    bottom: '10%',
    left: '0',
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
    pointerEvents: 'none',
    zIndex: '2147483647',
  });

  const textBg = document.createElement('div');
  textBg.id = 'webcaptioner-text-bg';
  Object.assign(textBg.style, {
    backgroundColor: 'rgba(18, 18, 24, 0.82)',
    padding: '10px 20px',
    borderRadius: '12px',
    color: 'white',
    fontFamily: 'sans-serif',
    fontSize: '24px',
    fontWeight: 'bold',
    textAlign: 'center',
    maxWidth: '80%',
    wordWrap: 'break-word',
    // High contrast black stroke outline
    textShadow: '-2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0px 0px 4px #000',
    display: 'none',
    boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
  });

  container.appendChild(textBg);
  document.body.appendChild(container);

  let hideTimeout = null;

  function getSpeakerColor(label) {
    const colors = [
      '#ff9999', '#99ccff', '#99ff99', '#ffcc99', '#cc99ff',
      '#ffff99', '#ff99cc', '#99ffff', '#ffccff', '#ccff99'
    ];
    let hash = 0;
    for (let i = 0; i < label.length; i++) {
      hash = label.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  }

  function parseSpeakerTags(text) {
    if (!text) return "";
    // Escape HTML to prevent injection
    let safeText = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
    
    const regex = /\[(Speaker\s*[^\]]+)\]:/gi;
    return safeText.replace(regex, (match, label) => {
      const color = getSpeakerColor(label);
      return `<br><span style="color: ${color}"><b>[${label}]:</b></span>`;
    }).replace(/^<br>/, ''); // Remove leading BR if it's the very first tag
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === 'showCaption') {
      if (msg.text) {
        textBg.innerHTML = parseSpeakerTags(msg.text);
        if (msg.fontSize) {
          textBg.style.fontSize = `${msg.fontSize}px`;
        }
        textBg.style.display = 'block';

        clearTimeout(hideTimeout);
        hideTimeout = setTimeout(() => {
          textBg.style.display = 'none';
        }, 10000); // Hide after 10s of silence
      } else {
        textBg.style.display = 'none';
      }
    } else if (msg.action === 'hideCaption') {
      textBg.style.display = 'none';
    }
  });
}
