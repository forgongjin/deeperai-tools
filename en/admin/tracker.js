/**
 * Deeper AI Tools — Privacy-First Analytics Tracker
 * All data stored in localStorage, never sent to any server.
 * View dashboard at: /en/admin/dashboard.html (password: wangcai2026)
 * Upgrade path: replace with GA4 when measurement ID is available.
 */
(function() {
  'use strict';
  
  const MAX_LOG_SIZE = 5000;
  const STORAGE_KEY = 'dtools_pv_log';
  
  // Generate or retrieve session ID
  let sessionId = sessionStorage.getItem('dtools_sid');
  if (!sessionId) {
    sessionId = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    sessionStorage.setItem('dtools_sid', sessionId);
  }
  
  function getDeviceType() {
    const w = window.innerWidth;
    if (w < 768) return 'mobile';
    if (w < 1024) return 'tablet';
    return 'desktop';
  }
  
  function getReferrer() {
    try {
      const ref = document.referrer;
      if (!ref) return 'direct';
      const url = new URL(ref);
      if (url.hostname === window.location.hostname) return 'internal';
      return url.hostname.replace('www.', '');
    } catch(e) {
      return 'direct';
    }
  }
  
  function getCountry() {
    // Rough country detection via navigator.language
    const lang = navigator.language || navigator.userLanguage || '';
    try {
      const region = lang.split('-')[1];
      if (region && region.length === 2) return region.toUpperCase();
    } catch(e) {}
    return 'Unknown';
  }
  
  function logPageView() {
    try {
      const log = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      
      log.push({
        page: window.location.pathname,
        ts: new Date().toISOString(),
        sid: sessionId,
        ref: getReferrer(),
        country: getCountry(),
        device: getDeviceType(),
        lang: navigator.language
      });
      
      // Trim to max size
      if (log.length > MAX_LOG_SIZE) {
        log.splice(0, log.length - MAX_LOG_SIZE);
      }
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(log));
    } catch(e) {
      // Silently fail — analytics are non-critical
    }
  }
  
  // Log on page load
  if (document.readyState === 'complete') {
    logPageView();
  } else {
    window.addEventListener('load', logPageView);
  }
})();
