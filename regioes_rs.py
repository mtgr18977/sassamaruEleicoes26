"""Mapeia os municípios do RS (código TSE) para mesorregião/microrregião do IBGE, cruzando por nome.
Saída: datasets/rs-municipios-regioes.csv. Requer rede (API de localidades do IBGE)."""
import gzip
import json
import urllib.request

import pandas as pd

from fetch_tse import normalizar_texto

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/43/municipios"
# Grafias que diferem entre TSE e IBGE (normalizadas): TSE -> IBGE
ALIAS = {}


def chave(s):
    return normalizar_texto(s).replace("'", " ").replace("-", " ").replace("’", " ")


if __name__ == "__main__":
    raw = urllib.request.urlopen(urllib.request.Request(URL), timeout=30).read()
    ibge = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)   # a API pode devolver gzip
    ib = pd.DataFrame([dict(ibge_id=m["id"], nome_ibge=m["nome"], meso=m["microrregiao"]["mesorregiao"]["nome"], micro=m["microrregiao"]["nome"]) for m in ibge])
    ib["k"] = ib.nome_ibge.map(chave)
    tse = pd.read_csv("datasets/tse-governador-rs-municipio.csv", dtype={"cod_municipio": str}).query("ano == 2022")[["cod_municipio", "municipio"]].drop_duplicates()
    tse["k"] = tse.municipio.map(chave).replace(ALIAS)
    m = tse.merge(ib, on="k", how="outer", indicator=True)
    print(m["_merge"].value_counts().to_dict())
    print(m[m["_merge"] != "both"][["municipio", "nome_ibge"]].to_string())
    ok = m[m["_merge"] == "both"].drop(columns=["_merge", "k"])
    ok.to_csv("datasets/rs-municipios-regioes.csv", index=False)
    print(ok.groupby("meso").size().to_dict())
