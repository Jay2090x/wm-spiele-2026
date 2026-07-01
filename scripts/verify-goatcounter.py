#!/usr/bin/env python3
import json
import sys
import urllib.request
from playwright.sync_api import sync_playwright

LIVE_URL = 'https://jay2090x.github.io/wm-spiele-2026/'
GC_COUNT = 'https://jay2090x.goatcounter.com/count'
GC_HOME = 'https://jay2090x.goatcounter.com/'
errors = []


def ok(name, detail=''):
    print(f'OK  {name}' + (f' — {detail}' if detail else ''))


def fail(name, detail=''):
    errors.append((name, detail))
    print(f'FAIL {name}' + (f' — {detail}' if detail else ''))


def http_status(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'verify-goatcounter/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.geturl()


def main():
    try:
        status, final = http_status(GC_HOME)
        if status == 200 and 'goatcounter.com' in final:
            ok('Dashboard erreichbar', final)
        else:
            fail('Dashboard erreichbar', f'{status} {final}')
    except Exception as exc:
        fail('Dashboard erreichbar', str(exc))

    try:
        test_url = GC_COUNT + '?p=/verify-test&t=verify&s=1920&b=0'
        status, _ = http_status(test_url)
        if status == 200:
            ok('Count-Endpoint')
        else:
            fail('Count-Endpoint', str(status))
    except Exception as exc:
        fail('Count-Endpoint', str(exc))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        hits = []

        def on_request(req):
            if 'jay2090x.goatcounter.com/count' in req.url:
                hits.append(req.url)

        page.on('request', on_request)
        page.route('https://ipwho.is/', lambda route: route.fulfill(
            status=200, content_type='application/json',
            body=json.dumps({'success': True, 'country_code': 'AT', 'ip': '127.0.0.1'}),
        ))
        page.goto(LIVE_URL, wait_until='networkidle', timeout=120000)
        page.wait_for_timeout(5000)

        if hits:
            ok('Seite sendet GoatCounter-Hit', hits[0][:80] + '…')
        else:
            fail('Seite sendet GoatCounter-Hit', 'kein Request an jay2090x.goatcounter.com/count')

        browser.close()

    if errors:
        sys.exit(1)
    print('All GoatCounter checks passed.')


if __name__ == '__main__':
    main()