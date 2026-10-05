"""Regenera tudo a partir dos CSVs: pesquisas -> Monte Carlo -> modelo do RS -> páginas (index.html, analise.html, rs.html e bancada.html).

  python atualizar.py   pesquisas.py, montecarlo.py, rs_modelo.py, projecao.py (1º turno), as três páginas e os testes

Antes de rodar com pesquisas novas, atualize HOJE e HORIZONTE em pesquisas.py e HOJE em rs_modelo.py.
O agregador (agregador.py) usa essas mesmas HOJE.
A projeção de 1/10 não é mais sobrescrita no repositório: está na tag projecao-1turno-2026-10-01.
"""
import subprocess
import sys

passos = ["pesquisas.py", "montecarlo.py", "rs_modelo.py", "projecao.py", "gerar_pagina_lula.py", "gerar_pagina_analise.py", "gerar_pagina_rs.py", "gerar_pagina_bancada.py"]
for p in passos:
    print(f"\n>>> python {p}")
    subprocess.run([sys.executable, p], check=True, stdout=subprocess.DEVNULL if p in ("montecarlo.py", "rs_modelo.py") else None)
print("\n>>> testes")
subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], check=True)
for t in ("eleicoes-model", "projecao-model", "chances-model", "rs-model"):
    subprocess.run(["node", f"tests/{t}.test.js"], check=True)
