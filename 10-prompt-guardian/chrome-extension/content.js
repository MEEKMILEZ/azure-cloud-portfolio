var API_URL = 'https://fn-promptguard-061l6f.azurewebsites.net/api/classify';
var OVERRIDE_URL = 'https://fn-promptguard-061l6f.azurewebsites.net/api/override';
var isScanning = false;
var guardianEnabled = true;

chrome.storage.local.get(['guardianEnabled'], function(result) {
  guardianEnabled = result.guardianEnabled !== false;
});
chrome.storage.onChanged.addListener(function(changes) {
  if (changes.guardianEnabled) guardianEnabled = changes.guardianEnabled.newValue;
});

function getPromptText() {
  // ChatGPT uses a contenteditable div with id="prompt-textarea" or a ProseMirror editor
  var el = document.getElementById('prompt-textarea');
  if (el) return el.innerText.trim();
  // Fallback: any contenteditable in main
  var ce = document.querySelector('main [contenteditable="true"]');
  if (ce) return ce.innerText.trim();
  return '';
}

function setPromptText(text) {
  var el = document.getElementById('prompt-textarea');
  if (el) {
    el.innerText = text;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    return;
  }
  var ce = document.querySelector('main [contenteditable="true"]');
  if (ce) {
    ce.innerText = text;
    ce.dispatchEvent(new Event('input', { bubbles: true }));
  }
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function classifyPrompt(text) {
  return fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-ID': 'chrome-extension' },
    body: JSON.stringify({ prompt: text })
  }).then(function(r) { return r.json(); });
}

function submitOverrideAPI(promptText, result, reason, justification) {
  return fetch(OVERRIDE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-ID': 'chrome-extension' },
    body: JSON.stringify({
      prompt: promptText,
      reason: reason,
      justification: justification || reason,
      original_action: result.action,
      original_category: result.category,
      original_severity: result.severity
    })
  }).then(function(r) { return r.json(); });
}

function removeModal() {
  var m = document.getElementById('pg-modal-overlay');
  if (m) m.remove();
}

function showModal(result, originalText) {
  removeModal();
  var action = (result.action || 'UNKNOWN').toUpperCase();
  var actionClass = action === 'ALLOW' ? 'pg-allow' : action === 'REDACT' ? 'pg-redact' : 'pg-block';
  var icon = action === 'ALLOW' ? '✅' : action === 'REDACT' ? '✂️' : '⛔';
  var label = action === 'ALLOW' ? 'Safe to Send' : action === 'REDACT' ? 'Sensitive — Redacted Version Available' : 'Blocked — Sensitive Data Detected';

  var flaggedHTML = '';
  if (result.flagged_content && result.flagged_content.length > 0) {
    flaggedHTML = '<div class="pg-section"><div class="pg-section-label">Flagged Content</div><div class="pg-flagged-list">';
    result.flagged_content.forEach(function(f) { flaggedHTML += '<div class="pg-flagged-item">' + escapeHtml(f) + '</div>'; });
    flaggedHTML += '</div></div>';
  }

  var redactedHTML = '';
  if (result.redacted_prompt) {
    var h = escapeHtml(result.redacted_prompt).replace(/\[REDACTED[^\]]*\]/g, function(m) { return '<span class="pg-redacted-tag">' + m + '</span>'; });
    redactedHTML = '<div class="pg-section"><div class="pg-section-label">Redacted Version</div><div class="pg-redacted-box">' + h + '</div></div>';
  }

  var buttonsHTML = '';
  if (action === 'ALLOW') {
    buttonsHTML = '<button class="pg-btn pg-btn-allow" id="pg-btn-send">Send to ChatGPT</button><button class="pg-btn pg-btn-cancel" id="pg-btn-cancel">Cancel</button>';
  } else if (action === 'REDACT') {
    buttonsHTML = '<button class="pg-btn pg-btn-redact" id="pg-btn-redacted">Send Redacted Version</button><button class="pg-btn pg-btn-cancel" id="pg-btn-cancel">Cancel</button>';
  } else {
    buttonsHTML = '<button class="pg-btn pg-btn-cancel" id="pg-btn-cancel">Don\'t Send</button><button class="pg-btn pg-btn-override" id="pg-btn-override">Override with Justification</button>';
  }

  var overlay = document.createElement('div');
  overlay.id = 'pg-modal-overlay';
  overlay.className = 'pg-overlay';
  overlay.innerHTML = '<div class="pg-modal">' +
    '<div class="pg-header"><div class="pg-shield">🛡️</div><div class="pg-title">Prompt Guardian</div></div>' +
    '<div class="pg-verdict ' + actionClass + '"><span class="pg-verdict-icon">' + icon + '</span><div><div class="pg-verdict-action">' + action + '</div><div class="pg-verdict-label">' + label + '</div></div></div>' +
    '<div class="pg-meta"><span class="pg-tag">Category: <strong>' + (result.category||'—') + '</strong></span><span class="pg-tag">Severity: <strong>' + (result.severity||'—') + '</strong></span><span class="pg-tag">Confidence: <strong>' + (result.confidence||'—') + '</strong></span></div>' +
    '<div class="pg-section"><div class="pg-section-label">Assessment</div><div class="pg-detail">' + escapeHtml(result.summary||'') + '</div></div>' +
    flaggedHTML + redactedHTML +
    '<div class="pg-buttons">' + buttonsHTML + '</div>' +
    '<div class="pg-audit">🔒 ' + (result.audit_ref||'audit pending') + '</div>' +
    '</div>';

  document.body.appendChild(overlay);

  // ALLOW — send original
  var sendBtn = document.getElementById('pg-btn-send');
  if (sendBtn) sendBtn.addEventListener('click', function() {
    removeModal();
    isScanning = false;
    guardianEnabled = false;
    setTimeout(function() {
      var btn = document.querySelector('[data-testid="send-button"], button[aria-label="Send prompt"]');
      if (btn) btn.click();
      setTimeout(function() { guardianEnabled = true; }, 1000);
    }, 100);
  });

  // REDACT — replace text then send
  var redactBtn = document.getElementById('pg-btn-redacted');
  if (redactBtn) redactBtn.addEventListener('click', function() {
    removeModal();
    isScanning = false;
    setPromptText(result.redacted_prompt || originalText);
    guardianEnabled = false;
    setTimeout(function() {
      var btn = document.querySelector('[data-testid="send-button"], button[aria-label="Send prompt"]');
      if (btn) btn.click();
      setTimeout(function() { guardianEnabled = true; }, 1000);
    }, 300);
  });

  // CANCEL
  var cancelBtn = document.getElementById('pg-btn-cancel');
  if (cancelBtn) cancelBtn.addEventListener('click', function() { removeModal(); isScanning = false; });

  // OVERRIDE — show justification form
  var overrideBtn = document.getElementById('pg-btn-override');
  if (overrideBtn) overrideBtn.addEventListener('click', function() {
    showOverrideForm(overlay, result, originalText);
  });

  // Close on overlay click
  overlay.addEventListener('click', function(e) { if (e.target === overlay) { removeModal(); isScanning = false; } });
}

function showOverrideForm(overlay, result, originalText) {
  var modal = overlay.querySelector('.pg-modal');
  modal.innerHTML = '<div class="pg-header"><div class="pg-shield">🛡️</div><div class="pg-title">Override — Justification Required</div></div>' +
    '<div class="pg-section"><div class="pg-section-label">Reason</div>' +
    '<select id="pg-or-reason" style="width:100%;padding:10px;background:#1a2236;border:1px solid #1e2a3e;border-radius:8px;color:#e2e8f0;font-size:14px;">' +
    '<option value="">Select a reason...</option><option value="approved_use_case">Approved use case</option><option value="test_data">Test data only</option><option value="client_authorized">Client authorized</option><option value="medical_necessity">Medical necessity</option><option value="other">Other</option></select></div>' +
    '<div class="pg-section"><div class="pg-section-label">Justification</div>' +
    '<textarea id="pg-or-text" placeholder="Explain why..." style="width:100%;min-height:70px;padding:10px;background:#1a2236;border:1px solid #1e2a3e;border-radius:8px;color:#e2e8f0;font-size:14px;resize:vertical;"></textarea></div>' +
    '<div style="font-size:12px;color:#94a3b8;background:rgba(202,138,4,0.08);border:1px solid rgba(202,138,4,0.2);border-radius:8px;padding:12px;margin-bottom:16px;">⚠️ This override will be logged and your manager notified automatically.</div>' +
    '<div class="pg-buttons"><button class="pg-btn pg-btn-cancel" id="pg-or-cancel">Cancel</button><button class="pg-btn pg-btn-override" id="pg-or-submit">Submit Override</button></div>';

  document.getElementById('pg-or-cancel').addEventListener('click', function() { removeModal(); isScanning = false; });
  document.getElementById('pg-or-submit').addEventListener('click', function() {
    var reason = document.getElementById('pg-or-reason').value;
    var justification = document.getElementById('pg-or-text').value.trim();
    if (!reason) { alert('Select a reason.'); return; }
    if (reason === 'other' && !justification) { alert('Provide justification.'); return; }

    submitOverrideAPI(originalText, result, reason, justification).then(function(data) {
      removeModal();
      isScanning = false;
      guardianEnabled = false;
      setTimeout(function() {
        var btn = document.querySelector('[data-testid="send-button"], button[aria-label="Send prompt"]');
        if (btn) btn.click();
        setTimeout(function() { guardianEnabled = true; }, 1000);
      }, 100);
    }).catch(function(err) {
      alert('Override failed: ' + err.message);
      isScanning = false;
    });
  });
}

// Main interceptor
document.addEventListener('click', function(e) {
  if (!guardianEnabled || isScanning) return;

  var sendBtn = document.querySelector('[data-testid="send-button"], button[aria-label="Send prompt"]');
  if (!sendBtn) return;
  if (!sendBtn.contains(e.target) && e.target !== sendBtn) return;

  var text = getPromptText();
  if (!text || text.length < 3) return;

  e.preventDefault();
  e.stopPropagation();
  e.stopImmediatePropagation();
  isScanning = true;

  classifyPrompt(text).then(function(result) {
    showModal(result, text);
  }).catch(function(err) {
    console.error('[Prompt Guardian] Error:', err);
    isScanning = false;
  });
}, true);

// Intercept Enter key
document.addEventListener('keydown', function(e) {
  if (!guardianEnabled || isScanning) return;
  if (e.key !== 'Enter' || e.shiftKey) return;

  var input = document.getElementById('prompt-textarea') || document.querySelector('main [contenteditable="true"]');
  if (!input || !input.contains(e.target)) return;

  var text = input.innerText.trim();
  if (!text || text.length < 3) return;

  e.preventDefault();
  e.stopPropagation();
  e.stopImmediatePropagation();
  isScanning = true;

  classifyPrompt(text).then(function(result) {
    showModal(result, text);
  }).catch(function(err) {
    console.error('[Prompt Guardian] Error:', err);
    isScanning = false;
  });
}, true);

console.log('[Prompt Guardian] Active on ' + window.location.hostname);
