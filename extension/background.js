const API_BASE = 'http://localhost:8000';

chrome.runtime.onMessage.addListener((message) => {
  if (message.type !== 'VIDEO_WATCHED') return;

  fetch(`${API_BASE}/api/v1/indexer/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message.data),
  })
    .then((res) => res.json())
    .then((data) => console.log('[Synapse] 수집 완료:', data))
    .catch((err) => console.error('[Synapse] 전송 실패:', err));
});
