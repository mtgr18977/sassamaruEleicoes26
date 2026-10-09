"""Regenera tudo a partir dos CSVs: pesquisas -> Monte Carlo -> modelo do RS -> páginas (index.html, analise*.html, segundo-turno.html, rs.html, bancada.html e analise-senado.html).

  python atualizar.py   pesquisas.py, montecarlo.py, rs_modelo.py, projecao.py (1º turno), as três páginas e os testes

Antes de rodar com pesquisas novas, atualize HOJE e HORIZONTE em pesquisas.py (só o 2º turno presidencial). HOJE em rs_modelo.py fica congelado em 2/10: o governador do RS foi decidido no 1º turno.
O agregador (agregador.py) usa essas mesmas HOJE.
A projeção do 1º turno fica congelada em HOJE_1T (2/10): é a previsão feita antes da votação, que a aba Análise compara com o resultado. Só o 2º turno anda com HOJE.
A projeção de 1/10 não é mais sobrescrita no repositório: está na tag projecao-1turno-2026-10-01.
"""
import subprocess
import sys

passos = ["pesquisas.py", "montecarlo.py", "rs_modelo.py", "projecao.py", "gerar_pagina_lula.py", "gerar_pagina_analise.py", "gerar_pagina_segundo_turno.py", "gerar_pagina_rs.py", "gerar_pagina_bancada.py", "gerar_paginas_analise_rs.py", "gerar_pagina_senado.py", "gerar_pagina_modelo.py", "nav.py"]
for p in passos:
    print(f"\n>>> python {p}")
    subprocess.run([sys.executable, p], check=True, stdout=subprocess.DEVNULL if p in ("montecarlo.py", "rs_modelo.py") else None)
print("\n>>> testes")
subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], check=True)
for t in ("eleicoes-model", "projecao-model", "chances-model", "rs-model"):
    subprocess.run(["node", f"tests/{t}.test.js"], check=True)
