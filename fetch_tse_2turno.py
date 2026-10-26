"""Baixa o resultado OFICIAL do 2º turno de presidente (25/10/2026) do portal de resultados do TSE (resultados.tse.jus.br), por UF e no Brasil, e grava
datasets/tse-presidente-2turno-uf.csv e datasets/resultado-2026-turno2.csv (o que a aba Resultado e avaliar_2turno.py leem).

  python fetch_tse_2turno.py            # 2º turno
  python fetch_tse_2turno.py --turno1   # 1º turno (mesmo formato, para comparar o comparecimento)
Os arquivos do portal seguem o padrão que o próprio aplicativo do TSE usa (lido no JavaScript dele): <base>/oficial/ele2026/<eleição>/dados/<uf>/<uf>-c0001-e<eleição com 6 dígitos>-u.json,
com eleição 6258 (2º turno federal) e uf em minúsculas ("br" = Brasil, "zz" = exterior). O portal limita o ritmo (HTTP 429): o script espera e tenta de novo.
Campos usados: carg[0].agr[].par[].cand[] (n = número, vap = votos nominais, pvapn = % dos válidos), e.c/e.a (comparecimento e abstenção), v.vb/v.vn (brancos e nulos), s.pst (% de seções)."""
import json
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

ELEICAO = {1: "6257", 2: "6258"}      # eleição federal de 1º e de 2º turno no portal do TSE
BASE = "https://resultados.tse.jus.br/oficial/ele2026/{ele}/dados/{uf}/{uf}-c0001-e00{ele}-u.json"
UFS = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to zz".split()


def baixar(uf, turno=2):
    req = urllib.request.Request(BASE.format(uf=uf, ele=ELEICAO[turno]), headers={"User-Agent": "Mozilla/5.0"})
    for tentativa in range(8):
        try:
            return json.load(urllib.request.urlopen(req, timeout=40))
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
        except Exception:
            pass
        time.sleep(4 + 3 * tentativa)
    raise RuntimeError(f"sem resposta do TSE para {uf}")


def linha(uf, d):
    cand = {c["n"]: c for ag in d["carg"][0]["agr"] for p in ag["par"] for c in p["cand"]}
    lula, flavio = int(cand["13"]["vap"]), int(cand["22"]["vap"])
    e, v, s = d["e"], d["v"], d["s"]
    return dict(uf=uf.upper(), votos_lula=lula, votos_flavio=flavio, votos_outros=int(v["vv"]) - lula - flavio, validos=int(v["vv"]), brancos=int(v["vb"]), nulos=int(v["vn"]), comparecimento=int(e["c"]), abstencao=int(e["a"]),
                eleitorado=int(e["te"]), secoes_apuradas_pct=float(s["pstn"]), gerado_em=f'{d["dg"]} {d["hg"]}')


def main():
    turno = 1 if "--turno1" in sys.argv else 2
    linhas = []
    for uf in ["br"] + UFS:
        d = baixar(uf, turno)
        linhas.append(linha(uf, d))
        print(uf, linhas[-1]["votos_lula"], linhas[-1]["votos_flavio"], linhas[-1]["secoes_apuradas_pct"], flush=True)
        time.sleep(2.5)
    t = pd.DataFrame(linhas)
    t["lula_pct_validos"] = (100 * t.votos_lula / (t.votos_lula + t.votos_flavio)).round(4)
    if turno == 1:                                   # só o 1º turno do portal (comparecimento por UF para comparar com o 2º)
        t.to_csv("datasets/tse-presidente-1turno-uf.csv", index=False)
        print("grava datasets/tse-presidente-1turno-uf.csv")
        return
    t.to_csv("datasets/tse-presidente-2turno-uf.csv", index=False)
    r = t[["uf", "lula_pct_validos"]].rename(columns={"lula_pct_validos": "lula_pct"})
    r["fonte"] = "TSE, resultados.tse.jus.br (oficial, 100% das seções)"
    r["obs"] = ""
    r.loc[r.uf == "BR", "obs"] = "Lula 64256232 x Flavio 59826041; abstencao 19.22%, brancos 1.12%, nulos 2.12% (TSE, 25/10/2026 23h27)"
    r.loc[r.uf == "ZZ", "obs"] = "exterior (fora das 27 UFs)"
    r.to_csv("datasets/resultado-2026-turno2.csv", index=False)
    print("grava datasets/tse-presidente-2turno-uf.csv e datasets/resultado-2026-turno2.csv")


if __name__ == "__main__":
    sys.exit(main())
