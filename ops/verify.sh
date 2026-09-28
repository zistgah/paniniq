#!/usr/bin/env bash
# ops/verify.sh: Panini Q's gate. Every clause of CONTRACT.md, checked by execution.
# © 1993–2026 Abhishek Choudhary. All rights reserved. AyeAI.
# SPDX-License-Identifier: GPL-3.0-or-later
# Exit 0 when nothing fails; 1 when a clause fails. UNJUDGED is reported, never counted a pass.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
LINE="© 1993–2026 Abhishek Choudhary. All rights reserved. AyeAI."
LICENCE_SHA=3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986
pass=0; fail=0; unj=0
chk() { local id="$1" what="$2"; shift 2; local out rc; out="$("$@" 2>&1)"; rc=$?
  if [ $rc -eq 0 ]; then printf '  PASS     %s  %s\n' "$id" "$what"; pass=$((pass+1))
  elif [ $rc -eq 3 ]; then printf '  UNJUDGED %s  %s: %s\n' "$id" "$what" "$(printf '%s' "$out" | tail -1)"; unj=$((unj+1))
  else printf '  FAIL     %s  %s\n' "$id" "$what"; printf '%s\n' "$out" | tail -8 | sed 's/^/           /'; fail=$((fail+1)); fi; }
have_sci() { python3 -c 'import numpy, scipy' 2>/dev/null || { echo "numpy and scipy are not installed; pip install -r requirements.txt"; return 3; }; }

p01() { local f bad=0
  for f in $(find . -path ./.git -prune -o \( -name '*.py' -o -name '*.sh' -o -name '*.html' \) -type f -print) \
           README.md CONTRACT.md CONTEXT.md GLOSSARY.md AGENTS.md PROVENANCE.md; do
    grep -qF "$LINE" "$f" || { echo "no copyright line: $f"; bad=1; }
    case "$f" in *.py|*.sh) grep -q 'SPDX-License-Identifier: GPL-3.0-or-later' "$f" || { echo "no SPDX line: $f"; bad=1; } ;; esac
  done; return $bad; }
p02() { ! grep -rIil 'independent researcher' --exclude-dir=.git --exclude=verify.sh . ; }
p03() { have_sci || return $?; python3 -m unittest discover -s tests 2>&1 | tail -3; python3 -m unittest discover -s tests >/dev/null 2>&1; }
p04() { have_sci || return $?
  rm -rf .gate && mkdir -p .gate && cp -a pedler tests .gate/
  python3 - <<'PY' || return 1
p = ".gate/pedler/hardware_bridge.py"; s = open(p, encoding="utf-8").read()
a = "abs(K[i, j]) / max_abs"; assert s.count(a) == 1, "mutation anchor moved"
open(p, "w", encoding="utf-8").write(s.replace(a, "K[i, j] / max_abs"))
PY
  if (cd .gate && python3 -m unittest tests.test_core.Frames >/dev/null 2>&1); then rm -rf .gate; echo "the suite passed with the zeroing bug put back"; return 1; fi
  rm -rf .gate; }
p05() { have_sci || return $?; timeout 600 python3 demo.py >/dev/null; }
p06() { [ "$(sha256sum LICENSE | cut -c1-64)" = "$LICENCE_SHA" ] || { echo "LICENSE is not the FSF's verbatim GPL-3.0 text"; return 1; }; }
p07() { local bad; bad="$(grep '\*\*Tested\*\*' README.md | grep -v 'tests/test_core.py')"; [ -z "$bad" ] || { echo "$bad"; return 1; }; }
p08() { local bad; bad="$(find . -path ./.git -prune -o \( -name __pycache__ -o -name '*.pyc' -o -name '*.tar.gz' -o -name '*.egg-info' \) -print)"; [ -z "$bad" ] || { echo "$bad"; return 1; }; }
p09() { local bad; bad="$(grep -nE '\$HOME|~/|/tmp|\.\./' ops/*.sh pedler/*.py demo.py tests/*.py | grep -v 'p09-exempt')"; [ -z "$bad" ] || { echo "$bad"; return 1; }; }   # p09-exempt
p10() { python3 - <<'PY'
import json, re, sys
m = json.load(open("misty.json", encoding="utf-8")); c = open("CITATION.cff", encoding="utf-8").read()
get = lambda k: (re.search(r'(?m)^%s:\s*"?(.*?)"?\s*$' % k, c) or [None, None])[1]
bad = [k for k, v in (("title", m["title"]), ("version", m["version"]), ("license", m["license"])) if get(k) != v]
if re.search(r"zenodo\.(0+|x+|X+)\b|XXXX", c + json.dumps(m)): bad.append("placeholder DOI")
print("disagree: " + ", ".join(bad) if bad else "", end=""); sys.exit(1 if bad else 0)
PY
}

echo "Panini Q: contract verification"
chk P01 "every source carries the copyright and SPDX lines"          p01
chk P02 "no affiliation other than AyeAI is claimed"                 p02
chk P03 "the test suite passes"                                      p03
chk P04 "the suite catches the anti-ferromagnetic zeroing bug"       p04
chk P05 "demo.py runs to completion"                                 p05
chk P06 "LICENSE is the FSF's verbatim GPL-3.0 text"                 p06
chk P07 "every row the README marks Tested names its test"           p07
chk P08 "no build artefacts"                                         p08
chk P09 "no path outside the folder is named"                        p09
chk P10 "misty.json and CITATION.cff agree; no placeholder DOI"      p10
echo "  $pass passed, $fail failed, $unj unjudged"
[ $fail -eq 0 ]
