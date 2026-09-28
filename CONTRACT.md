# CONTRACT: Panini Q

© 1993–2026 Abhishek Choudhary. All rights reserved. AyeAI.

Each clause is checked by `bash ops/verify.sh`. A clause the gate cannot judge is reported as
UNJUDGED, never as a pass.

| Clause | What holds | Check |
|---|---|---|
| 1 | Every source and script carries the copyright line and an SPDX identifier. | P01 |
| 2 | No affiliation other than AyeAI is claimed. | P02 |
| 3 | The test suite passes. | P03 |
| 4 | The suite catches the anti-ferromagnetic zeroing bug if it is reintroduced. | P04 |
| 5 | `demo.py` runs to completion. | P05 |
| 6 | `LICENSE` is the FSF's verbatim GPL-3.0 text. | P06 |
| 7 | Every status row the README marks Tested names the test that asserts it. | P07 |
| 8 | No build artefacts are committed. | P08 |
| 9 | No script names a path outside its folder: no home, temp or parent paths. | P09 |
| 10 | `misty.json` and `CITATION.cff` agree on title, version and licence; no placeholder DOI. | P10 |

Licence: code GPL-3.0-or-later. Authorship: Abhishek Choudhary, AyeAI.
