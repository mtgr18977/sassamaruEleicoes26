"""Gera bancada.html (aba da bancada legislativa do RS; dados embutidos) a partir de apps/bancada.template.html."""
import json

import nav

import numpy as np

import rs_bancada


def _json(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(type(o))


out = rs_bancada.construir()
html = nav.moldura(open("apps/bancada.template.html", encoding="utf-8").read(), "bancada.html").replace("__DATA__", json.dumps(out, ensure_ascii=False, default=_json))
open("bancada.html", "w", encoding="utf-8").write(html)
print("bancada.html", len(html) // 1024, "KB")
