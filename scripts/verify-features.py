#!/usr/bin/env python3
import json
import sys
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8765/'
errors = []


def ok(name, detail=''):
    print(f'OK  {name}' + (f' — {detail}' if detail else ''))


def fail(name, detail=''):
    errors.append((name, detail))
    print(f'FAIL {name}' + (f' — {detail}' if detail else ''))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.route('https://ipwho.is/', lambda route: route.fulfill(
            status=200, content_type='application/json',
            body=json.dumps({'success': True, 'country_code': 'AT', 'ip': '127.0.0.1'}),
        ))
        page.goto(URL, wait_until='networkidle', timeout=120000)
        page.wait_for_timeout(10000)

        # No Gr column
        ths = page.locator('.matches-table thead th').all_text_contents()
        if 'Gr' not in ths and len(ths) == 4:
            ok('Gr-Spalte entfernt', str(ths))
        else:
            fail('Gr-Spalte entfernt', str(ths))

        # Date rows
        dates = page.locator('tr.date-row').count()
        if dates >= 1:
            ok('Datumszeilen', f'{dates} rows')
        else:
            fail('Datumszeilen', 'none')

        # No bottom ko path
        if page.locator('.br-ko-path').count() == 0:
            ok('Kein Extra-Feld unten')
        else:
            fail('Kein Extra-Feld unten', 'br-ko-path still present')

        # Integrated bracket nodes
        af = page.locator('[data-br-tier="af"] .br-node').count()
        vf = page.locator('[data-br-tier="vf"] .br-node').count()
        hf = page.locator('[data-br-tier="hf"] .br-node').count()
        if af >= 8 and vf >= 4 and hf >= 2:
            ok('Spielbaum integriert', f'AF={af} VF={vf} HF={hf}')
        else:
            fail('Spielbaum integriert', f'AF={af} VF={vf} HF={hf}')

        svg_paths = page.locator('.bracket-svg path').count()
        if svg_paths >= 20:
            ok('Goldene Linien', f'{svg_paths} paths')
        else:
            fail('Goldene Linien', f'only {svg_paths}')

        # Stats open matches
        labels = page.locator('#stats-grid .lbl').all_text_contents()
        if 'Offene Spiele' in labels and 'Höchstsieg' not in labels:
            ok('Statistik offene Spiele')
        else:
            fail('Statistik', str(labels))

        # Finished all KO
        head = page.locator('#finished-head').inner_text()
        finished = page.locator('#finished-list .finished-row').count()
        if '24h' not in head and finished >= 1:
            ok('Alle KO beendet', f'{finished} — {head}')
        else:
            fail('Alle KO beendet', f'{finished} — {head}')

        browser.close()

    if errors:
        sys.exit(1)
    print('All checks passed.')


if __name__ == '__main__':
    main()