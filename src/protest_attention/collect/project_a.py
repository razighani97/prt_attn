"""Project A collection: pageviews for every movement's protest and issue
articles, in English and in the Hindi and Bengali equivalents where they exist,
and GDELT article volume via BigQuery as the second, independent measure.

Run: make collect-a
"""

import json
from datetime import date

from protest_attention.collect import gdelt_bq
from protest_attention.collect import wikipedia as w
from protest_attention.movements import MOVEMENTS, window
from protest_attention.paths import INTERIM

# Which raw file is which movement, role and language. Derived, so it lives in
# interim and is rewritten on every run.
MANIFEST = INTERIM / "project_a_manifest.json"

OTHER_LANGS = ("hi", "bn")


def run(today: date | None = None) -> list[dict]:
    today = today or date.today()
    done = []
    for m in MOVEMENTS:
        start, end = window(m, today)
        for role, title in (("protest", m.protest), ("issue", m.issue)):
            en = w.collect_article("a", "en", title, start, end)
            done.append({"movement": m.key, "role": role, "lang": "en", "path": en["path"]})
            if en["article"]["missing"]:
                continue
            for lang, ltitle in w.langlinks("en", en["article"]["canonical"], OTHER_LANGS).items():
                rec = w.collect_article("a", lang, ltitle, start, end)
                done.append({"movement": m.key, "role": role, "lang": lang, "path": rec["path"]})
            print(f"{m.key:8} {role:8} {start}..{end} done", flush=True)
        news = gdelt_bq.collect("a", m.key, start, end)
        done.append({"movement": m.key, "role": "news", "lang": "gdelt", "path": news["path"]})
        print(f"{m.key:8} gdelt    {news['gb_scanned']} GB", flush=True)
    INTERIM.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(done, indent=1))
    return done


if __name__ == "__main__":
    run()
