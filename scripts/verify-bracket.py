#!/usr/bin/env python3
"""Verify WM bracket tree wiring through all KO rounds."""
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


BRACKET_TEST_JS = r'''
async () => {
  const leftCtx = { r32: R32_LEFT, tree: BRACKET_TREE.left };
  const rightCtx = { r32: R32_RIGHT, tree: BRACKET_TREE.right };

  function setWinner(id, homeKey, awayKey, winnerKey) {
    const homeScore = winnerKey === homeKey ? '2' : '0';
    const awayScore = winnerKey === awayKey ? '2' : '0';
    liveScores[id] = {
      id, homeScore, awayScore, state: 'post',
      homeWinner: winnerKey === homeKey,
      awayWinner: winnerKey === awayKey,
      hasPenalties: false, penHome: null, penAway: null,
    };
  }

  function clearScores() {
    liveScores = {};
    knockoutMeta = {};
  }

  function sides(id, feeders, ctx) {
    return resolveBracketSides(id, feeders, ctx);
  }

  function abbr(key) {
    return key ? (TEAM_ABBR[key] || key) : null;
  }

  function pairLabel(s) {
    return `${abbr(s.homeKey) || '?'}/${abbr(s.awayKey) || '?'}`;
  }

  const out = { checks: [], scenarios: [] };

  // Poisoned ESPN meta (real bug): Mexico/England on 760505
  clearScores();
  knockoutMeta['760505'] = { id: '760505', homeEn: 'Mexico', awayEn: 'England' };
  const bad = sides('760505', BRACKET_TREE.left.af[3], leftCtx);
  out.checks.push({
    name: '760505 ignores ESPN Mexico/England',
    pass: !(bad.homeKey === 'mexiko' && bad.awayKey === 'england'),
    detail: pairLabel(bad),
  });

  const mexEngRight = sides('760506', BRACKET_TREE.right.af[1], rightCtx);
  out.checks.push({
    name: 'Mexico/England nur rechts (760506 Feeder)',
    pass: mexEngRight.homeKey === null && mexEngRight.awayKey === null,
    detail: 'ohne R32-Sieger: ?/?',
  });

  // Simulate all R32 with home-team wins
  clearScores();
  for (const m of R32_ALL) setWinner(m.id, m.home, m.away, m.home);
  const afLeft505 = sides('760505', BRACKET_TREE.left.af[3], leftCtx);
  out.checks.push({
    name: '760505 = USA-Sieger vs BEL-Sieger',
    pass: afLeft505.homeKey === 'usa' && afLeft505.awayKey === 'belgien',
    detail: pairLabel(afLeft505),
  });
  const afRight506 = sides('760506', BRACKET_TREE.right.af[1], rightCtx);
  out.checks.push({
    name: '760506 = MEX-Sieger vs ENG-Sieger',
    pass: afRight506.homeKey === 'mexiko' && afRight506.awayKey === 'england',
    detail: pairLabel(afRight506),
  });

  // Full tournament: home wins every match
  clearScores();
  for (const m of R32_ALL) setWinner(m.id, m.home, m.away, m.home);

  function playBracketSide(ctx) {
    for (const af of ctx.tree.af) {
      const s = sides(af.id, af, ctx);
      if (s.homeKey && s.awayKey) setWinner(af.id || `sim-af-${s.homeKey}`, s.homeKey, s.awayKey, s.homeKey);
    }
    for (const vf of ctx.tree.vf) {
      const s = sides(vf.id, vf, ctx);
      if (s.homeKey && s.awayKey) setWinner(vf.id, s.homeKey, s.awayKey, s.homeKey);
    }
    const hf = ctx.tree.hf;
    const hs = sides(hf.id, hf, ctx);
    if (hs.homeKey && hs.awayKey) setWinner(hf.id, hs.homeKey, hs.awayKey, hs.homeKey);
    return getBracketWinner(hf.id, hf, ctx);
  }

  const leftWin = playBracketSide(leftCtx);
  const rightWin = playBracketSide(rightCtx);
  const fin = sides(BRACKET_TREE.final.id, { hf: ['left', 'right'] }, leftCtx);
  if (fin.homeKey && fin.awayKey) setWinner(BRACKET_TREE.final.id, fin.homeKey, fin.awayKey, fin.homeKey);
  const champ = getBracketWinner(BRACKET_TREE.final.id, { hf: ['left', 'right'] }, leftCtx);

  out.scenarios.push({
    name: 'home-wins-all',
    leftHF: leftWin,
    rightHF: rightWin,
    finalist: pairLabel(fin),
    champion: abbr(champ),
  });

  // Alternate: away wins all R32, then home wins KO
  clearScores();
  for (const m of R32_ALL) setWinner(m.id, m.home, m.away, m.away);
  playBracketSide(leftCtx);
  playBracketSide(rightCtx);
  const fin2 = sides(BRACKET_TREE.final.id, { hf: ['left', 'right'] }, leftCtx);
  out.scenarios.push({
    name: 'r32-away-then-home',
    finalist: pairLabel(fin2),
  });

  // Validate every AF slot only uses teams from its R32 feeders
  clearScores();
  knockoutMeta['760505'] = { id: '760505', homeEn: 'Mexico', awayEn: 'England' };
  knockoutMeta['760502'] = { id: '760502', homeEn: 'Canada', awayEn: 'Morocco' };
  const afErrors = [];
  for (const [side, ctx] of [['left', leftCtx], ['right', rightCtx]]) {
    ctx.tree.af.forEach((af, i) => {
      const allowed = [...bracketAllowedKeys(af, ctx)];
      const s = sides(af.id, af, ctx);
      for (const k of [s.homeKey, s.awayKey]) {
        if (k && allowed.length && !allowed.includes(k)) {
          afErrors.push(`${side} AF${i + 1} (${af.id || '?'}) team ${k}`);
        }
      }
    });
  }
  out.checks.push({
    name: 'AF-Feeder ohne Fremdteams (poisoned ESPN)',
    pass: afErrors.length === 0,
    detail: afErrors.join('; ') || 'ok',
  });

  return out;
}
'''


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.route('https://ipwho.is/', lambda route: route.fulfill(
            status=200, content_type='application/json',
            body=json.dumps({'success': True, 'country_code': 'AT', 'ip': '127.0.0.1'}),
        ))
        page.goto(URL, wait_until='networkidle', timeout=120000)
        page.wait_for_timeout(3000)
        result = page.evaluate(BRACKET_TEST_JS)

        for chk in result.get('checks', []):
            if chk.get('pass'):
                ok(chk['name'], chk.get('detail', ''))
            else:
                fail(chk['name'], chk.get('detail', ''))

        for sc in result.get('scenarios', []):
            ok(f"Szenario {sc['name']}", json.dumps(sc, ensure_ascii=False))

        # DOM: 760505 must not show MEX+ENG together
        page.evaluate('''() => {
          knockoutMeta["760505"] = { id: "760505", homeEn: "Mexico", awayEn: "England" };
          renderBracket();
        }''')
        page.wait_for_timeout(500)
        node505 = page.locator('[data-espn="760505"] .br-abbr').all_text_contents()
        text = '/'.join(node505)
        if 'MEX' in text and 'ENG' in text:
            fail('DOM 760505', text)
        else:
            ok('DOM 760505 ohne MEX/ENG', text or '(noch offen)')

        browser.close()

    if errors:
        sys.exit(1)
    print('All bracket checks passed.')


if __name__ == '__main__':
    main()