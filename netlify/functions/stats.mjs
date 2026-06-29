import { corsHeaders, dayKey, getAnalyticsStore } from './_lib.mjs';

async function listByPrefix(store, prefix) {
  const { blobs } = await store.list({ prefix });
  const out = {};
  for (const blob of blobs) {
    const val = Number(await store.get(blob.key, { type: 'text' })) || 0;
    const label = blob.key.slice(prefix.length);
    if (label && val > 0) out[label] = val;
  }
  return out;
}

function lastDays(count = 30) {
  const days = [];
  const end = new Date();
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(end);
    d.setUTCDate(d.getUTCDate() - i);
    days.push(dayKey(d));
  }
  return days;
}

export default async (request) => {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (request.method !== 'GET') {
    return new Response('Method not allowed', { status: 405, headers: corsHeaders() });
  }

  const url = new URL(request.url);
  const token = url.searchParams.get('token') || '';
  const expected = process.env.ANALYTICS_DASHBOARD_TOKEN || '';
  if (expected && token !== expected) {
    return new Response('Unauthorized', { status: 401, headers: corsHeaders() });
  }

  const daysParam = Math.min(90, Math.max(7, Number(url.searchParams.get('days') || 30)));
  const store = getAnalyticsStore();
  const days = lastDays(daysParam);
  const today = dayKey();

  const series = [];
  let totalViews = Number(await store.get('views:total', { type: 'text' })) || 0;
  let rangeViews = 0;
  let todayViews = 0;
  let todayVisitors = 0;

  for (const day of days) {
    const views = Number(await store.get(`views:${day}`, { type: 'text' })) || 0;
    const visitors = Number(await store.get(`visitors:${day}`, { type: 'text' })) || 0;
    rangeViews += views;
    if (day === today) {
      todayViews = views;
      todayVisitors = visitors;
    }
    series.push({ day, views, visitors });
  }

  const pages = await listByPrefix(store, `pages:${today}:`);
  const sources = await listByPrefix(store, `sources:${today}:`);
  const terms = await listByPrefix(store, `terms:${today}:`);
  const hours = await listByPrefix(store, `hours:${today}:`);

  const hourSeries = Array.from({ length: 24 }, (_, h) => {
    const key = String(h).padStart(2, '0');
    return { hour: key, views: hours[key] || 0 };
  });

  const sortDesc = (obj) =>
    Object.entries(obj)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);

  const payload = {
    updated: new Date().toISOString(),
    rangeDays: daysParam,
    totalViews,
    rangeViews,
    today: { views: todayViews, visitors: todayVisitors },
    series,
    hourSeries,
    topPages: sortDesc(pages).slice(0, 10),
    topSources: sortDesc(sources).slice(0, 10),
    topTerms: sortDesc(terms).slice(0, 10),
  };

  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { ...corsHeaders(), 'Content-Type': 'application/json' },
  });
};