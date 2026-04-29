/**
 * Prompt Guardian — Content Script
 * Intercepts prompt submission on AI chat platforms,
 * sends to Azure classify endpoint, shows result modal.
 */

const API_URL = 'https://fn-promptguard-061l6f.azurewebsites.net/api/classify';
let isScanning = false;
let guardianEnabled = true;

// Check if Guardian is enabled
chrome.storage.local.get(['guardianEnabled'], (result) => {
  guardianEnabled = result.guardianEnabled !== false;
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.guardianEnabled) {
    guardianEnabled = changes.guardianEnabled.newValue;
  }
});

/**
 * Detect which platform we're on and find the input + submit elements
 */
function getPlatformConfig() {
  const host = window.location.hostname;

  if (host.includes('chatgpt.com') || host.includes('chat.openai.com')) {
    return {
      name: 'ChatGPT',
      getInput: () => document.querySelector('#prompt-textarea, [contenteditable="true"]'),
      getSubmitBtn: () => document.querySelector('[data-testid="send-button"], button[aria-label="Send prompt"]'),
      getPromptText: (el) => el.innerText || el.textContent
    };
  }

  if (host.includes('claude.ai')) {
    return {
      name: 'Claude',
      getInput: () => document.querySelector('[contenteditable="true"]'),
      getSubmitBtn: () => document.querySelector('button[aria-label="Send Message"], button[type="submit"]'),
      getPromptText: (el) => el.innerText || el.textContent
    };
  }

  if (host.includes('copilot.microsoft.com')) {
    return {
      name: 'Copilot',
      getInput: () => document.querySelector('#searchbox, textarea'),
      getSubmitBtn: () => document.querySelector('button[aria-label="Submit"]'),
      getPromptText: (el) => el.value || el.innerText || el.textContent
    };
  }

  return null;
}

/**
 * Call the classify endpoint
 */
async function classifyPrompt(text) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': 'chrome-extension'
    },
    body: JSON.stringify({ prompt: text })
  });
  return response.json();
}

/**
 * Create and show the Guardian modal
 */
function showModal(result, originalText, onAllow, onBlock) {
  // Remove existing modal if any
  const existing = document.getElementById('pg-modal-overlay');
  if (existing) existing.remove();

  const action = (result.action || 'UNKNOWN').toUpperCase();

  const overlay = document.createElement('div');
  overlay.id = 'pg-modal-overlay';
  overlay.className = 'pg-overlay';

  const actionClass = action === 'ALLOW' ? 'pg-allow' : action === 'REDACT' ? 'pg-redact' : 'pg-block';
  const actionIcon = action === 'ALLOW' ? '✅' : action === 'REDACT' ? '✂️' : '⛔';
  const actionLabel = action === 'ALLOW' ? 'Safe to Send'
    : action === 'REDACT' ? 'Sensitive Content Detected — Redacted Version Available'
    : 'Blocked — Sensitive Data Detected';

  let flaggedHTML = '';
  if (result.flagged_content && result.flagged_content.length > 0) {
    flaggedHTML = `
      <div class="pg-section">
        <div class="pg-section-label">Flagged Content</div>
        <div class="pg-flagged-list">
          ${result.flagged_content.map(f => `<div class="pg-flagged-item">${escapeHtml(f)}</div>`).join('')}
        </div>
      </div>
    `;
  }

  let redactedHTML = '';
  if (result.redacted_prompt) {
    const highlighted = escapeHtml(result.redacted_prompt).replace(
      /\[REDACTED[^\]]*\]/g,
      match => `<span class="pg-redacted-tag">${match}</span>`
    );
    redactedHTML = `
      <div class="pg-section">
        <div class="pg-section-label">Redacted Version — Safe to Send</div>
        <div class="pg-redacted-box">${highlighted}</div>
      </div>
    `;
  }

  let buttonsHTML = '';
  if (action === 'ALLOW') {
    buttonsHTML = `
      <button class="pg-btn pg-btn-allow" id="pg-btn-send">Send to ${getPlatformConfig()?.name || 'AI'}</button>
      <button class="pg-btn pg-btn-cancel" id="pg-btn-cancel">Cancel</button>
    `;
  } else if (action === 'REDACT') {
    buttonsHTML = `
      <button class="pg-btn pg-btn-redact" id="pg-btn-redacted">Send Redacted Version</button>
      <button class="pg-btn pg-btn-cancel" id="pg-btn-cancel">Cancel — Don't Send</button>
    `;
  } else {
    buttonsHTML = `
      <button class="pg-btn pg-btn-block" id="pg-btn-cancel">Understood — Don't Send</button>
    `;
  }

  overlay.innerHTML = `
    <div class="pg-modal">
      <div class="pg-header">
        <div class="pg-shield">🛡️</div>
        <div class="pg-title">Prompt Guardian</div>
      </div>

      <div class="pg-verdict ${actionClass}">
        <span class="pg-verdict-icon">${actionIcon}</span>
        <div>
          <div class="pg-verdict-action">${action}</div>
          <div class="pg-verdict-label">${actionLabel}</div>
        </div>
      </div>

      <div class="pg-meta">
        <span class="pg-tag">Category: <strong>${result.category || '—'}</strong></span>
        <span class="pg-tag">Severity: <strong>${result.severity || '—'}</strong></span>
        <span class="pg-tag">Confidence: <strong>${result.confidence || '—'}</strong></span>
      </div>

      <div class="pg-section">
        <div class="pg-section-label">Assessment</div>
        <div class="pg-detail">${escapeHtml(result.summary || '')}</div>
      </div>

      ${flaggedHTML}
      ${redactedHTML}

      <div class="pg-buttons">
        ${buttonsHTML}
      </div>

      <div class="pg-audit">🔒 Logged: ${result.audit_ref || 'audit pending'}</div>
    </div>
  `;

  document.body.appendChild(overlay);

  // Event handlers
  const sendBtn = document.getElementById('pg-btn-send');
  const redactBtn = document.getElementById('pg-btn-redacted');
  const cancelBtn = document.getElementById('pg-btn-cancel');

  if (sendBtn) {
    sendBtn.addEventListener('click', () => {
      overlay.remove();
      onAllow(originalText);
    });
  }

  if (redactBtn) {
    redactBtn.addEventListener('click', () => {
      overlay.remove();
      onAllow(result.redacted_prompt || originalText);
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      overlay.remove();
      onBlock();
    });
  }

  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.remove();
      onBlock();
    }
  });

  // Close on Escape
  document.addEventListener('keydown', function escHandler(e) {
    if (e.key === 'Escape') {
      overlay.remove();
      onBlock();
      document.removeEventListener('keydown', escHandler);
    }
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Intercept form submission
 */
function interceptSubmit(platform) {
  // Use event delegation on the document to catch dynamically added buttons
  document.addEventListener('click', async (e) => {
    if (!guardianEnabled || isScanning) return;

    const submitBtn = platform.getSubmitBtn();
    if (!submitBtn) return;

    // Check if the clicked element is or is inside the submit button
    if (!submitBtn.contains(e.target) && e.target !== submitBtn) return;

    const inputEl = platform.getInput();
    if (!inputEl) return;

    const promptText = platform.getPromptText(inputEl).trim();
    if (!promptText || promptText.length < 3) return;

    // Stop the original submit
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    isScanning = true;

    try {
      const result = await classifyPrompt(promptText);

      showModal(result, promptText,
        // onAllow — simulate clicking submit again with Guardian disabled temporarily
        (textToSend) => {
          isScanning = false;
          // If redacted, replace the input content
          if (textToSend !== promptText) {
            if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
              inputEl.value = textToSend;
              inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            } else {
              inputEl.innerText = textToSend;
              inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            }
          }
          // Temporarily disable guardian and click submit
          guardianEnabled = false;
          setTimeout(() => {
            submitBtn.click();
            setTimeout(() => { guardianEnabled = true; }, 500);
          }, 100);
        },
        // onBlock
        () => {
          isScanning = false;
        }
      );
    } catch (err) {
      console.error('[Prompt Guardian] Classification failed:', err);
      isScanning = false;
    }
  }, true); // useCapture = true to intercept before other handlers

  // Also intercept Enter key submission
  document.addEventListener('keydown', async (e) => {
    if (!guardianEnabled || isScanning) return;
    if (e.key !== 'Enter' || e.shiftKey) return;

    const inputEl = platform.getInput();
    if (!inputEl) return;
    if (!inputEl.contains(e.target) && e.target !== inputEl) return;

    const promptText = platform.getPromptText(inputEl).trim();
    if (!promptText || promptText.length < 3) return;

    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    isScanning = true;

    try {
      const result = await classifyPrompt(promptText);

      showModal(result, promptText,
        (textToSend) => {
          isScanning = false;
          if (textToSend !== promptText) {
            if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
              inputEl.value = textToSend;
            } else {
              inputEl.innerText = textToSend;
            }
            inputEl.dispatchEvent(new Event('input', { bubbles: true }));
          }
          guardianEnabled = false;
          setTimeout(() => {
            inputEl.dispatchEvent(new KeyboardEvent('keydown', {
              key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true
            }));
            setTimeout(() => { guardianEnabled = true; }, 500);
          }, 100);
        },
        () => { isScanning = false; }
      );
    } catch (err) {
      console.error('[Prompt Guardian] Classification failed:', err);
      isScanning = false;
    }
  }, true);
}

/**
 * Initialize — wait for the platform to load, then attach interceptor
 */
function init() {
  const platform = getPlatformConfig();
  if (!platform) return;

  console.log(`[Prompt Guardian] Active on ${platform.name}`);

  // Wait for the submit button to appear (SPAs load dynamically)
  const observer = new MutationObserver(() => {
    const btn = platform.getSubmitBtn();
    if (btn) {
      observer.disconnect();
      interceptSubmit(platform);
      console.log(`[Prompt Guardian] Interceptor attached on ${platform.name}`);
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // Also try immediately
  const btn = platform.getSubmitBtn();
  if (btn) {
    interceptSubmit(platform);
    console.log(`[Prompt Guardian] Interceptor attached on ${platform.name}`);
  }
}

// Start
init();
