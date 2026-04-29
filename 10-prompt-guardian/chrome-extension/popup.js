const toggle = document.getElementById('toggleGuardian');
const label = document.getElementById('statusLabel');

chrome.storage.local.get(['guardianEnabled'], function(result) {
  var enabled = result.guardianEnabled !== false;
  toggle.checked = enabled;
  label.textContent = enabled ? 'Active' : 'Disabled';
  label.style.color = enabled ? '#4ade80' : '#f87171';
});

toggle.addEventListener('change', function() {
  var enabled = toggle.checked;
  chrome.storage.local.set({ guardianEnabled: enabled });
  label.textContent = enabled ? 'Active' : 'Disabled';
  label.style.color = enabled ? '#4ade80' : '#f87171';
});
