document.addEventListener('DOMContentLoaded', () => {
  const fontFamilySelect = document.getElementById('fontFamilySelect');
  const textColorPicker = document.getElementById('textColorPicker');
  const hexDisplay = document.getElementById('hexDisplay');
  const strokeThicknessSlider = document.getElementById('strokeThicknessSlider');
  const strokeThicknessValue = document.getElementById('strokeThicknessValue');
  const previewBox = document.getElementById('previewBox');
  const statusDiv = document.getElementById('status');

  const defaultFontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  const defaultTextColor = '#ffffff';
  const defaultStrokeThickness = 2;

  function getStrokeTextShadow(thickness) {
    const t = parseInt(thickness, 10);
    if (t === 0) return 'none';
    return `-${t}px -${t}px 0 #000, ${t}px -${t}px 0 #000, -${t}px ${t}px 0 #000, ${t}px ${t}px 0 #000, 0px 0px 4px #000`;
  }

  function updatePreview() {
    const font = fontFamilySelect.value;
    const color = textColorPicker.value;
    const stroke = strokeThicknessSlider.value;

    if (hexDisplay) hexDisplay.textContent = color;
    if (strokeThicknessValue) strokeThicknessValue.textContent = `${stroke}px`;

    if (previewBox) {
      previewBox.style.fontFamily = font;
      previewBox.style.color = color;
      previewBox.style.textShadow = getStrokeTextShadow(stroke);
    }
  }

  function saveSettings() {
    const fontFamily = fontFamilySelect.value;
    const textColor = textColorPicker.value;
    const strokeThickness = parseInt(strokeThicknessSlider.value, 10);

    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({
        fontFamily: fontFamily,
        textColor: textColor,
        strokeThickness: strokeThickness
      }, () => {
        if (statusDiv) {
          statusDiv.textContent = 'Settings saved';
          setTimeout(() => {
            if (statusDiv.textContent === 'Settings saved') {
              statusDiv.textContent = '';
            }
          }, 2000);
        }
      });
    }
  }

  // Load existing settings
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get({
      fontFamily: defaultFontFamily,
      textColor: defaultTextColor,
      strokeThickness: defaultStrokeThickness
    }, (items) => {
      if (items.fontFamily && fontFamilySelect) fontFamilySelect.value = items.fontFamily;
      if (items.textColor && textColorPicker) textColorPicker.value = items.textColor;
      if (items.strokeThickness !== undefined && strokeThicknessSlider) strokeThicknessSlider.value = items.strokeThickness;
      updatePreview();
    });
  } else {
    updatePreview();
  }

  if (fontFamilySelect) {
    fontFamilySelect.addEventListener('change', () => {
      updatePreview();
      saveSettings();
    });
  }

  if (textColorPicker) {
    textColorPicker.addEventListener('input', () => {
      updatePreview();
      saveSettings();
    });
  }

  if (strokeThicknessSlider) {
    strokeThicknessSlider.addEventListener('input', () => {
      updatePreview();
      saveSettings();
    });
  }
});
