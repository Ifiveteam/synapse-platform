let lastTrackedVideoId = '';

function extractVideoId(url) {
  const watchMatch = url.match(/[?&]v=([^&]+)/);
  if (watchMatch) return watchMatch[1];
  const shortsMatch = url.match(/\/shorts\/([^?&]+)/);
  if (shortsMatch) return shortsMatch[1];
  return null;
}

function getVideoData() {
  const url = window.location.href;

  const isWatchPage = url.includes('/watch');
  const isShortsPage = url.includes('/shorts/');

  if (!isWatchPage && !isShortsPage) return null;

  // 제목
  const titleEl =
    document.querySelector('h1.ytd-watch-metadata yt-formatted-string') ||
    document.querySelector('h1.title yt-formatted-string') ||
    document.querySelector('ytd-reel-video-renderer h2 yt-formatted-string');
  const title = titleEl?.textContent?.trim();
  if (!title) return null;

  // 채널
  const channelEl =
    document.querySelector('ytd-channel-name#channel-name a') ||
    document.querySelector('#channel-name a');
  const channel = channelEl?.textContent?.trim() || '';
  const channelUrl = channelEl?.href || '';

  // 영상 길이
  const video = document.querySelector('video');
  const duration = video && isFinite(video.duration) ? Math.round(video.duration) : 0;

  const isShorts = isShortsPage || duration <= 60;

  // video ID 기준으로 정규화된 URL
  const videoId = extractVideoId(url);
  const cleanUrl = videoId
    ? `https://www.youtube.com/watch?v=${videoId}`
    : url;

  return {
    title,
    channel,
    channel_url: channelUrl,
    url: cleanUrl,
    watched_at: new Date().toISOString(),
    duration,
    is_shorts: isShorts,
  };
}

function tryTrack() {
  const url = window.location.href;
  console.log('[Synapse] tryTrack 호출:', url);
  const videoId = extractVideoId(url);
  if (!videoId) {
    console.log('[Synapse] videoId 없음, 스킵');
    return;
  }
  if (videoId === lastTrackedVideoId) {
    console.log('[Synapse] 이미 수집한 영상, 스킵:', videoId);
    return;
  }

  lastTrackedVideoId = videoId;

  setTimeout(() => {
    const data = getVideoData();
    if (!data) return;

    try {
      chrome.runtime.sendMessage({ type: 'VIDEO_WATCHED', data });
      console.log('[Synapse] 전송 완료:', data.title);
    } catch (e) {
      console.error('[Synapse] 전송 실패:', e);
    }
  }, 2500);
}

// YouTube는 SPA라 URL 변경을 감지해야 함
const observer = new MutationObserver(tryTrack);
observer.observe(document.body, { childList: true, subtree: true });

// 첫 진입 처리
tryTrack();
