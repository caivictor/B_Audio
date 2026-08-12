// content.js - Injected into the active tab to display captions

if (!window.__webCaptionerInitialized) {
  window.__webCaptionerInitialized = true;
  
  // Host element for Shadow DOM encapsulation (ADV-017)
  const host = document.createElement('div');
  host.id = 'webcaptioner-host';
  Object.assign(host.style, {
    position: 'fixed',
    bottom: '0',
    left: '0',
    width: '100%',
    height: '0',
    overflow: 'visible',
    zIndex: '2147483647',
    pointerEvents: 'none',
    margin: '0',
    padding: '0',
    border: 'none'
  });

  const shadow = host.attachShadow({ mode: 'open' });

  // Styles isolated inside Shadow DOM (ADV-016, ADV-017)
  const style = document.createElement('style');
  style.textContent = `
    :host {
      all: initial;
      position: fixed;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 0;
      overflow: visible;
      z-index: 2147483647;
      pointer-events: none;
    }
    #webcaptioner-overlay {
      position: fixed;
      bottom: 10%;
      left: 0;
      width: 100%;
      display: flex;
      justify-content: center;
      pointer-events: none;
      z-index: 2147483647;
      box-sizing: border-box;
    }
    #webcaptioner-text-bg {
      background-color: rgba(18, 18, 24, 0.82);
      padding: 10px 20px;
      border-radius: 12px;
      color: white;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 24px;
      font-weight: bold;
      text-align: center;
      max-width: 80%;
      max-height: 70vh;
      overflow-y: auto;
      word-wrap: break-word;
      box-sizing: border-box;
      line-height: 1.4;
      text-shadow: -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0px 0px 4px #000;
      display: none;
      box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
  `;
  shadow.appendChild(style);

  const container = document.createElement('div');
  container.id = 'webcaptioner-overlay';

  const textBg = document.createElement('div');
  textBg.id = 'webcaptioner-text-bg';

  container.appendChild(textBg);
  shadow.appendChild(container);

  // Attach host element to document body or fullscreen element (ADV-015)
  function attachHost() {
    const target = document.fullscreenElement || document.body;
    if (target && host.parentNode !== target) {
      target.appendChild(host);
    }
  }

  document.addEventListener('fullscreenchange', attachHost);
  attachHost();

  let hideTimeout = null;

  let currentFontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  let currentTextColor = '#ffffff';
  let currentStrokeThickness = 2;

  function applyCustomStyles(fontFamily, textColor, strokeThickness) {
    if (fontFamily) currentFontFamily = fontFamily;
    if (textColor) currentTextColor = textColor;
    if (strokeThickness !== undefined) currentStrokeThickness = strokeThickness;

    if (textBg) {
      textBg.style.fontFamily = currentFontFamily;
      textBg.style.color = currentTextColor;
      const t = parseInt(currentStrokeThickness, 10);
      if (t === 0) {
        textBg.style.textShadow = 'none';
      } else {
        textBg.style.textShadow = `-${t}px -${t}px 0 #000, ${t}px -${t}px 0 #000, -${t}px ${t}px 0 #000, ${t}px ${t}px 0 #000, 0px 0px 4px #000`;
      }
    }
  }

  // Load custom styling options from chrome.storage.local
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(['fontFamily', 'textColor', 'strokeThickness'], (items) => {
      applyCustomStyles(items.fontFamily, items.textColor, items.strokeThickness);
    });

    chrome.storage.onChanged.addListener((changes, areaName) => {
      if (areaName === 'local') {
        const font = changes.fontFamily ? changes.fontFamily.newValue : undefined;
        const color = changes.textColor ? changes.textColor.newValue : undefined;
        const stroke = changes.strokeThickness ? changes.strokeThickness.newValue : undefined;
        applyCustomStyles(font, color, stroke);
      }
    });
  }

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
    let safeText = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    const regex = /\[(Speaker\s*[^\]]+)\]:?/gi;
    const matches = Array.from(safeText.matchAll(regex));

    if (matches.length === 0) {
      return safeText.replace(/\n/g, '<br>');
    }

    let result = '';
    let lastIdx = 0;

    for (let i = 0; i < matches.length; i++) {
      const match = matches[i];
      const label = match[1].trim();
      const matchStart = match.index;
      const matchEnd = matchStart + match[0].length;

      let prefix = safeText.slice(lastIdx, matchStart);
      if (i > 0) {
        if (prefix && !prefix.trimEnd().endsWith('<br>') && !prefix.trimEnd().endsWith('\n')) {
          prefix += '<br>';
        } else if (!prefix) {
          prefix = '<br>';
        }
      }
      prefix = prefix.replace(/\n/g, '<br>');
      result += prefix;

      const nextStart = (i + 1 < matches.length) ? matches[i + 1].index : safeText.length;
      let segmentText = safeText.slice(matchEnd, nextStart).replace(/\n/g, '<br>');

      const color = getSpeakerColor(label);
      result += `<span style="color: ${color}"><b>[${label}]:</b>${segmentText}</span>`;

      lastIdx = nextStart;
    }

    // Clean up newlines so \n[Speaker X] doesn't cause <br><br> (ADV-019)
    result = result.replace(/\n<br>/g, '<br>').replace(/<br>\n/g, '<br>').replace(/\n/g, '<br>');

    // Remove leading <br> tags
    return result.replace(/^(<br>)+/, '');
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === 'showCaption') {
      if (msg.text) {
        textBg.innerHTML = parseSpeakerTags(msg.text);
        if (msg.fontSize) {
          const fontSizeNum = parseInt(msg.fontSize, 10);
          if (!isNaN(fontSizeNum)) {
            const clampedSize = Math.max(12, Math.min(72, fontSizeNum));
            textBg.style.fontSize = `${clampedSize}px`;
          }
        }
        if (msg.fontFamily || msg.textColor || msg.strokeThickness !== undefined) {
          applyCustomStyles(msg.fontFamily, msg.textColor, msg.strokeThickness);
        }
        textBg.style.display = 'block';
        textBg.scrollTop = textBg.scrollHeight;

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
