#!/usr/bin/env python3
"""Verify TV column shows stream links for many countries (mocked geo)."""
import json
import sys
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8765/'
errors = []

EXPECT_STREAM = {
    'AT': ('ORF', 'Servus'),
    'DE': ('ARD', 'ZDF'),
    'CH': ('SRF',),
    'US': ('Fox',),
    'AU': ('SBS',),
    'ES': ('RTVE',),
    'HR': ('HRT',),
    'PH': ('Aleph',),
    'GB': ('BBC',),
    'FR': ('TF1',),
    'IT': ('RAI',),
    'NL': ('NPO',),
    'BR': ('CazéTV',),
    'JP': ('NHK',),
    'KR': ('KBS',),
}

EXPECT_NOSTREAM = ('FR',)  # only if we want FR to stream - we added TF1 so remove
EXPECT_NOSTREAM = ('XX',)  # fictional country


def ok(name, detail=''):
    print(f'OK  {name}' + (f' — {detail}' if detail else ''))


def fail(name, detail=''):
    errors.append((name, detail))
    print(f'FAIL {name}' + (f' — {detail}' if detail else ''))


def check_country(page, cc):
    page.route('https://ipwho.is/', lambda route: route.fulfill(
        status=200, content_type='application/json',
        body=json.dumps({'success': True, 'country_code': cc, 'country': cc, 'ip': '127.0.0.1'}),
    ))
    page.goto(URL, wait_until='networkidle', timeout=120000)
    page.wait_for_timeout(8000)

    nostream = page.locator('.tv-nostream').count()
    links = page.locator('a.tv').all_text_contents()
    labels = [t.replace(' ↗', '').strip() for t in links if t.strip()]

    if cc in EXPECT_STREAM:
        expected = EXPECT_STREAM[cc]
        if nostream > 0 and not labels:
            fail(f'{cc} stream', f'got NO STREAM ({nostream}x), expected one of {expected}')
            return
        if not any(any(e in lbl for e in expected) for lbl in labels):
            fail(f'{cc} stream', f'labels={labels[:5]}, expected {expected}')
            return
        ok(f'{cc} stream', labels[0] if labels else '—')
        return

    if cc in EXPECT_NOSTREAM:
        if nostream < 1:
            fail(f'{cc} NO STREAM', f'labels={labels[:3]}')
        else:
            ok(f'{cc} NO STREAM')


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for cc in list(EXPECT_STREAM.keys()) + list(EXPECT_NOSTREAM):
            page = browser.new_page()
            check_country(page, cc)
            page.close()
        browser.close()

    if errors:
        for name, detail in errors:
            print(f'  • {name}: {detail}')
        sys.exit(1)
    print('All TV country checks passed.')


if __name__ == '__main__':
    main()