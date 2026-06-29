/**
 * Visitor Analytics – embed snippet
 * Backend: https://github.com/Jay2090x/visitor-analytics
 */
(function (window, document) {
  'use strict';

  var script = document.currentScript;
  var endpoint = (script && script.getAttribute('data-endpoint')) || '/api/collect';
  var site = (script && script.getAttribute('data-site')) || location.hostname;
  var ownerKey = 'va_owner_skip';
  var sentKey = 'va_sent';

  function readParams() {
    var params = new URLSearchParams(location.search);
    return {
      utm_source: params.get('utm_source') || '',
      utm_medium: params.get('utm_medium') || '',
      utm_campaign: params.get('utm_campaign') || '',
      utm_term: params.get('utm_term') || '',
      utm_content: params.get('utm_content') || '',
    };
  }

  function parseSearchTerm() {
    var ref = document.referrer;
    if (!ref) return '';
    try {
      var url = new URL(ref);
      var host = url.hostname.toLowerCase();
      if (host.indexOf('google.') !== -1 || host.indexOf('bing.') !== -1 || host.indexOf('duckduckgo.') !== -1) {
        return url.searchParams.get('q') || '';
      }
    } catch (e) {}
    return '';
  }

  function shouldSkip() {
    try {
      if (localStorage.getItem(ownerKey) === '1') return true;
      if (sessionStorage.getItem(sentKey) === '1') return true;
    } catch (e) {}
    if (/bot|crawl|spider|slurp|facebookexternalhit|WhatsApp|preview/i.test(navigator.userAgent)) return true;
    return false;
  }

  function markOwnerSkip() {
    try { localStorage.setItem(ownerKey, '1'); } catch (e) {}
  }

  window.VisitorAnalytics = {
    markAsOwner: markOwnerSkip,
    track: send,
  };

  function send() {
    if (shouldSkip()) return;

    var utm = readParams();
    var payload = {
      site: site,
      path: location.pathname + location.search,
      referrer: document.referrer || '',
      title: document.title || '',
      term: parseSearchTerm(),
      utm_source: utm.utm_source,
      utm_medium: utm.utm_medium,
      utm_campaign: utm.utm_campaign,
      utm_term: utm.utm_term,
      utm_content: utm.utm_content,
      lang: navigator.language || '',
      screen: (window.screen && screen.width) ? screen.width + 'x' + screen.height : '',
    };

    try { sessionStorage.setItem(sentKey, '1'); } catch (e) {}

    var body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([body], { type: 'application/json' }));
      return;
    }
    fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body, keepalive: true }).catch(function () {});
  }

  if (document.readyState === 'complete') send();
  else window.addEventListener('load', send, { once: true });
})(window, document);