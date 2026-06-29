import {
  clientIp,
  corsHeaders,
  dayKey,
  getAnalyticsStore,
  hashIp,
  hourKey,
  inc,
  isOwnerIp,
  parseReferrer,
  sanitizePath,
  sanitizeTerm,
  trackUniqueVisitor,
} from './_lib.mjs';

export default async (request) => {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405, headers: corsHeaders() });
  }

  let body = {};
  try {
    body = await request.json();
  } catch {
    return new Response('Invalid JSON', { status: 400, headers: corsHeaders() });
  }

  const ip = clientIp(request.headers);
  if (isOwnerIp(ip)) {
    return new Response(JSON.stringify({ ok: true, skipped: 'owner' }), {
      status: 200,
      headers: { ...corsHeaders(), 'Content-Type': 'application/json' },
    });
  }

  const store = getAnalyticsStore();
  const now = new Date();
  const day = dayKey(now);
  const hour = hourKey(now);
  const salt = process.env.ANALYTICS_SALT || 'change-me';
  const visitorHash = hashIp(ip, salt);

  const path = sanitizePath(body.path || '/');
  const ref = parseReferrer(body.referrer || '');
  const utmTerm = sanitizeTerm(body.utm_term || '');
  const utmSource = sanitizeTerm(body.utm_source || '');
  const searchTerm = sanitizeTerm(body.term || utmTerm || ref.term);

  const source = utmSource
    ? utmSource.charAt(0).toUpperCase() + utmSource.slice(1)
    : ref.source;

  await inc(store, `views:${day}`);
  await inc(store, `views:total`);
  await inc(store, `hours:${day}:${hour}`);
  await inc(store, `pages:${day}:${path}`);
  await inc(store, `sources:${day}:${source}`);
  await inc(store, `mediums:${day}:${ref.medium || 'referral'}`);
  if (searchTerm) await inc(store, `terms:${day}:${searchTerm.toLowerCase()}`);

  const isNew = await trackUniqueVisitor(store, day, visitorHash);

  return new Response(JSON.stringify({ ok: true, unique: isNew }), {
    status: 200,
    headers: { ...corsHeaders(), 'Content-Type': 'application/json' },
  });
};