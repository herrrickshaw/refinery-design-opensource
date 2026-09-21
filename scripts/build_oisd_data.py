"""Write ``refinery_design/data/oisd_standards.json`` from OISD's own published list.

Source: https://www.oisd.gov.in/oisd-standards ("OISD Standard/GDN/RP No", "Standard Name", "Current edition in vogue"),
fetched 21 Sep 2026 with a plain HTTP GET (system curl validates the certificate; Python's urllib and WebFetch do not).  Only the list is stored -
the standards themselves are sold by OISD and were NOT read; requirement details elsewhere in this repo are labelled with
the secondary source and a confidence level.

Run: python scripts/build_oisd_data.py     (needs network access)
"""
import html
import json
import re
import subprocess
from pathlib import Path

URL = "https://www.oisd.gov.in/oisd-standards"


def main() -> None:
    # System curl validates OISD's certificate chain; Python's urllib does not (missing intermediate) - never disable verification.
    raw = subprocess.run(["curl", "-sL", "--fail", "-A", "Mozilla/5.0", URL], capture_output=True, text=True, check=True).stdout
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", raw, flags=re.S):
        cells = [re.sub(r"\\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)]
        cells = [c for c in cells if c]
        if len(cells) >= 4 and cells[1].startswith("OISD-"):
            out[cells[1]] = {"title": cells[2], "edition": cells[3]}
    dest = Path(__file__).resolve().parents[1] / "refinery_design" / "data" / "oisd_standards.json"
    dest.write_text(json.dumps({"source": URL, "fetched": "2026-09-21", "count": len(out), "standards": out}, indent=1))
    print("wrote", dest, len(out), "standards")


if __name__ == "__main__":
    main()
