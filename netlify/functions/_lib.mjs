import { createHash } from 'node:crypto';
import { getStore } from '@netlify/blobs';

const STORE = 'visitor-analytics';

export function getAnalyticsStore() {
  return getStore({ name: STORE, consistency: 'strong' });
}

export function clientIp(headers) {
  return (
    headers.get('x-nf-client-connection-ip') ||
    headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    ''
  );
}

export function hashIp(ip, salt = '') {
  if (!ip) return '';
  return createHash('sha256').update(`${salt}:${ip}`).digest('hex').slice(0, 20);
}

export function ownerIps() {
  return (process.env.ANALYTICS_OWNER_IPS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function isOwnerIp(ip) {
  const owners = ownerIps();
  return owners.length > 0 && owners.includes(ip);
}

export function dayKey(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

export function hourKey(date = new Date()) {
  return String(date.getUTCHours()).padStart(2, '0');
}

export function parseReferrer(referrer) {
  if (!referrer) return { source: 'Direct', medium: 'direct', term: '' };
  try {
    const url = new URL(referrer);
    const host = url.hostname.replace(/^www\./, '').toLowerCase();
    if (host.includes('google.')) {
      return { source: 'Google', medium: 'search', term: url.searchParams.get('q') || '' };
    }
    if (host.includes('bing.')) {
      return { source: 'Bing', medium: 'search', term: url.searchParams.get('q') || '' };
    }
    if (host.includes('duckduckgo.')) {
      return { source: 'DuckDuckGo', medium: 'search', term: url.searchParams.get('q') || '' };
    }
    if (host === 't.co' || host.includes('twitter.') || host === 'x.com') {
      return { source: 'Twitter / X', medium: 'social', term: '' };
    }
    if (host.includes('facebook.') || host === 'fb.com' || host === 'l.facebook.com') {
      return { source: 'Facebook', medium: 'social', term: '' };
    }
    if (host.includes('instagram.')) return { source: 'Instagram', medium: 'social', term: '' };
    if (host.includes('reddit.')) return { source: 'Reddit', medium: 'social', term: '' };
    if (host.includes('whatsapp.') || host === 'wa.me') return { source: 'WhatsApp', medium: 'social', term: '' };
    if (host.includes('telegram.') || host === 't.me') return { source: 'Telegram', medium: 'social', term: '' };
    if (host.includes('youtube.') || host === 'youtu.be') return { source: 'YouTube', medium: 'social', term: '' };
    return { source: host, medium: 'referral', term: '' };
  } catch {
    return { source: 'Unknown', medium: 'referral', term: '' };
  }
}

export function corsHeaders(origin = '*') {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Cache-Control': 'no-store',
  };
}

export async function inc(store, key, by = 1) {
  const current = Number(await store.get(key, { type: 'text' })) || 0;
  await store.set(key, String(current + by));
  return current + by;
}

export async function trackUniqueVisitor(store, day, visitorHash) {
  if (!visitorHash) return false;
  const key = `uv:${day}:${visitorHash}`;
  const seen = await store.get(key, { type: 'text' });
  if (seen) return false;
  await store.set(key, '1');
  await inc(store, `visitors:${day}`);
  return true;
}

export function sanitizePath(path = '/') {
  const p = String(path).split('?')[0] || '/';
  return p.length > 120 ? p.slice(0, 120) : p;
}

export function sanitizeTerm(term = '') {
  const t = String(term).trim().slice(0, 80);
  return t.replace(/[^\w\säöüÄÖÜß\-]/gi, '').trim();
}