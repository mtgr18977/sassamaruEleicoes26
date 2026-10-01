"""Regenera tudo a partir dos CSVs: pesquisas -> Monte Carlo -> modelo do RS -> páginas (index.html e rs.html).

  python atualizar.py              pesquisas.py, montecarlo.py, rs_modelo.py, as duas páginas e os testes
  python atualizar.py --projecao   também refaz a projeção do 1º turno (SOBRESCREVE modelos/projecao-1turno*;
                                   a versão de 1/10 está congelada na tag projecao-1turno-2026-10-01)
"""
import subprocess
import sys

passos = ["pesquisas.py", "montecarlo.py", "rs_modelo.py"] + (["projecao.py"] if "--projecao" in sys.argv else []) + ["gerar_pagina_lula.py", "gerar_pagina_rs.py"]
for p in passos:
    print(f"\n>>> python {p}")
    subprocess.run([sys.executable, p], check=True, stdout=subprocess.DEVNULL if p in ("montecarlo.py", "rs_modelo.py") else None)
print("\n>>> testes")
subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], check=True)
for t in ("eleicoes-model", "projecao-model", "chances-model", "rs-model"):
    subprocess.run(["node", f"tests/{t}.test.js"], check=True)
