"""ETL do Senado: votos por candidato a Senador (1º turno) em 2018 e 2026 e senadores em exercício.

Entradas (zips oficiais do TSE, "votação por candidato, município e zona"; baixe com curl em um diretório vazio e passe o caminho):
  python fetch_tse_senado.py 2026 caminho/votacao_candidato_munzona_2026.zip
  python fetch_tse_senado.py 2018 caminho/votacao_candidato_munzona_2018.zip
  python fetch_tse_senado.py atual            # API de dados abertos do Senado (rede)
Saídas: datasets/tse-senado-AAAA.csv (uma linha por candidato: UF, nome, partido, federação, votos nominais, votos válidos (sem anulados sub judice), situação) e
datasets/senado-atual.csv (os 81 senadores em exercício, partido, UF e fim do mandato).
Só lê os arquivos por UF (o *_BRASIL.csv é o mesmo dado, 3 GB) e só as linhas de Senador."""
import json
import sys
import urllib.request
import zipfile

import pandas as pd

D = "datasets/"
COLS = ["SG_UF", "DS_CARGO", "NR_CANDIDATO", "SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "SG_FEDERACAO", "NM_COLIGACAO", "QT_VOTOS_NOMINAIS", "QT_VOTOS_NOMINAIS_VALIDOS", "DS_SIT_TOT_TURNO", "NR_TURNO"]
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()


def agregar_zip(caminho, ano):
    z = zipfile.ZipFile(caminho)
    nomes = {n.rsplit("_", 1)[-1][:-4]: n for n in z.namelist() if n.endswith(".csv")}
    saida = []
    for uf in UFS:
        n = nomes.get(uf)
        if n is None:
            raise SystemExit(f"{uf} ausente em {caminho}")
        with z.open(n) as f:
            for ch in pd.read_csv(f, sep=";", encoding="latin1", usecols=lambda c: c in COLS, chunksize=400_000, dtype=str):
                s = ch[(ch.DS_CARGO == "Senador") & (ch.NR_TURNO == "1")]
                if len(s):
                    saida.append(s.assign(QT_VOTOS_NOMINAIS=s.QT_VOTOS_NOMINAIS.astype(int), QT_VOTOS_NOMINAIS_VALIDOS=s.QT_VOTOS_NOMINAIS_VALIDOS.astype(int)))
        print(uf, end=" ", flush=True)
    d = pd.concat(saida)
    chave = ["SG_UF", "SQ_CANDIDATO"]
    g = d.groupby(chave).agg(nome=("NM_URNA_CANDIDATO", "first"), partido=("SG_PARTIDO", "first"), federacao=("SG_FEDERACAO", "first"),
                              coligacao=("NM_COLIGACAO", "first"), votos=("QT_VOTOS_NOMINAIS", "sum"), votos_validos=("QT_VOTOS_NOMINAIS_VALIDOS", "sum"),
                              situacao=("DS_SIT_TOT_TURNO", "first")).reset_index()
    g.insert(0, "ano", ano)
    g = g.rename(columns={"SG_UF": "uf", "SQ_CANDIDATO": "sq"}).sort_values(["uf", "votos"], ascending=[True, False])
    g["federacao"] = g.federacao.where(g.federacao != "#NULO#", "")
    g["coligacao"] = g.coligacao.where(g.coligacao != "#NULO#", "")
    return g


def senadores_atuais():
    req = urllib.request.Request("https://legis.senado.leg.br/dadosabertos/senador/lista/atual", headers={"Accept": "application/json"})
    L = json.load(urllib.request.urlopen(req, timeout=60))["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    linhas = []
    for p in L:
        i, m = p["IdentificacaoParlamentar"], p["Mandato"]
        fins = [m[k]["DataFim"] for k in ("PrimeiraLegislaturaDoMandato", "SegundaLegislaturaDoMandato") if k in m]
        linhas.append(dict(uf=i["UfParlamentar"], nome=i["NomeParlamentar"], partido=i["SiglaPartidoParlamentar"], mandato_fim=max(fins), titular=m.get("DescricaoParticipacao", "")))
    d = pd.DataFrame(linhas).sort_values(["uf", "nome"])
    d["fonte"] = "API de dados abertos do Senado (/senador/lista/atual)"
    return d


if __name__ == "__main__":
    modo = sys.argv[1]
    if modo == "atual":
        d = senadores_atuais()
        d["acesso"] = pd.Timestamp.today().strftime("%Y-%m-%d")
        d.to_csv(D + "senado-atual.csv", index=False)
        print(len(d), "senadores;", (d.mandato_fim.str[:4] == "2027").sum(), "com mandato até 2027")
    else:
        d = agregar_zip(sys.argv[2], int(modo))
        d.to_csv(D + f"tse-senado-{modo}.csv", index=False)
        print("\n", len(d), "candidatos;", (d.situacao == "ELEITO").sum(), "eleitos")
