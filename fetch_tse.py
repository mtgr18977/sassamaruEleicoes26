#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_tse.py — Fase 0 do Sassamaru Eleições.

Baixa do TSE (Dados Abertos) a votação para PRESIDENTE por município e zona,
classifica os candidatos em blocos (PT / anti-PT / outros) e salva CSVs no projeto.

COMO RODAR (na sua máquina; o sandbox do Claude não acessa o TSE):

    pip install pandas
    python fetch_tse.py                      # 2002, 2006, 2010, 2014, 2018, 2022
    python fetch_tse.py --anos 2018 2022     # só alguns anos
    python fetch_tse.py --inspecionar 2022   # mostra colunas/arquivos do zip (debug)
    python fetch_tse.py --sem-detalhe        # não baixa aptos/brancos/nulos (mais rápido)
    python fetch_tse.py --offline            # só usa zips já em datasets/tse_raw/

Se o download automático falhar (404, bloqueio de rede), baixe os zips à mão em
https://dadosabertos.tse.jus.br e coloque em datasets/tse_raw/ com os nomes:
    votacao_candidato_munzona_AAAA.zip
    detalhe_votacao_munzona_AAAA.zip
Depois rode com --offline.

SAÍDAS (em datasets/):
    tse-presidente-municipio.csv   1 linha por (ano, turno, município)
    tse-presidente-uf.csv          agregado por UF (inclui "ZZ" = voto no exterior)
    tse-presidente-capitais.csv    só as 27 capitais (subconjunto do municipal)
    tse-presidente-nacional.csv    total Brasil, usado na verificação

BLOCOS:
    pt      candidato do PT (Lula, Dilma, Haddad)
    antipt  o adversário do PT no 2º turno daquele ano (Serra, Alckmin, Aécio,
            Bolsonaro). O mesmo número de candidato é usado no 1º turno.
    outros  todo o resto (Marina, Ciro, Garotinho, Tebet, ...)
    Ajustes manuais: ANTIPT_OVERRIDE abaixo.

OBSERVAÇÕES:
    - cod_municipio é o código do TSE, NÃO o do IBGE.
    - Votos válidos = soma dos votos nominais (para presidente não há voto de legenda).
    - Nomes de colunas mudam entre anos; o script tenta aliases conhecidos e, se
      não achar, mostra as colunas reais do arquivo (use --inspecionar).
    - No fim, compara o total nacional com o resultado oficial; divergência > 0,15 p.p.
      gera aviso (provável problema de parsing ou de classificação de blocos).
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #

ANOS_PADRAO = [2002, 2006, 2010, 2014, 2018, 2022]

BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele"
URL_CANDIDATO = BASE_URL + "/votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"
URL_DETALHE = BASE_URL + "/detalhe_votacao_munzona/detalhe_votacao_munzona_{ano}.zip"

# Se a classificação automática do adversário do PT falhar em algum ano,
# informe o número do candidato aqui. Ex.: {2026: 22}
ANTIPT_OVERRIDE: dict[int, int] = {}

# Referência oficial (% de votos válidos do PT) — para sanity check, não para o modelo.
# Confira no site do TSE se quiser ter certeza; tolerância de 0,15 p.p.
OFICIAL_PT = {
    (2002, 1): 46.44, (2002, 2): 61.27,
    (2006, 1): 48.61, (2006, 2): 60.83,
    (2010, 1): 46.91, (2010, 2): 56.05,
    (2014, 1): 41.59, (2014, 2): 51.64,
    (2018, 1): 29.28, (2018, 2): 44.87,
    (2022, 1): 48.43, (2022, 2): 50.90,
}
TOLERANCIA_PP = 0.15

CAPITAIS = {
    "AC": "RIO BRANCO", "AL": "MACEIO", "AP": "MACAPA", "AM": "MANAUS",
    "BA": "SALVADOR", "CE": "FORTALEZA", "DF": "BRASILIA", "ES": "VITORIA",
    "GO": "GOIANIA", "MA": "SAO LUIS", "MT": "CUIABA", "MS": "CAMPO GRANDE",
    "MG": "BELO HORIZONTE", "PA": "BELEM", "PB": "JOAO PESSOA", "PR": "CURITIBA",
    "PE": "RECIFE", "PI": "TERESINA", "RJ": "RIO DE JANEIRO", "RN": "NATAL",
    "RS": "PORTO ALEGRE", "RO": "PORTO VELHO", "RR": "BOA VISTA",
    "SC": "FLORIANOPOLIS", "SP": "SAO PAULO", "SE": "ARACAJU", "TO": "PALMAS",
}

# Nomes de coluna possíveis (o TSE mudou o layout ao longo dos anos).
ALIASES_CANDIDATO = {
    "turno": ["NR_TURNO", "NUM_TURNO"],
    "uf": ["SG_UF", "SIGLA_UF"],
    "cod_municipio": ["CD_MUNICIPIO", "CODIGO_MUNICIPIO", "COD_MUN_TSE"],
    "municipio": ["NM_MUNICIPIO", "NOME_MUNICIPIO"],
    "zona": ["NR_ZONA", "NUMERO_ZONA", "NUM_ZONA"],
    "cargo": ["DS_CARGO", "DESCRICAO_CARGO"],
    "numero": ["NR_CANDIDATO", "NUMERO_CANDIDATO", "NUM_CAND"],
    "nome": ["NM_URNA_CANDIDATO", "NOME_URNA_CANDIDATO", "NM_CANDIDATO", "NOME_CANDIDATO"],
    "partido": ["SG_PARTIDO", "SIGLA_PARTIDO"],
    "votos": ["QT_VOTOS_NOMINAIS", "TOTAL_VOTOS", "QT_VOTOS"],
}
OBRIGATORIAS_CANDIDATO = ["turno", "uf", "cod_municipio", "municipio", "cargo", "numero", "votos"]

ALIASES_DETALHE = {
    "turno": ["NR_TURNO", "NUM_TURNO"],
    "uf": ["SG_UF", "SIGLA_UF"],
    "cod_municipio": ["CD_MUNICIPIO", "CODIGO_MUNICIPIO", "COD_MUN_TSE"],
    "cargo": ["DS_CARGO", "DESCRICAO_CARGO"],
    "aptos": ["QT_APTOS", "QTD_APTOS"],
    "comparecimento": ["QT_COMPARECIMENTO", "QTD_COMPARECIMENTO"],
    "brancos": ["QT_VOTOS_BRANCOS", "QTD_VOTOS_BRANCOS"],
    "nulos": ["QT_VOTOS_NULOS", "QTD_VOTOS_NULOS"],
}
OBRIGATORIAS_DETALHE = ["turno", "uf", "cod_municipio", "cargo", "aptos", "comparecimento"]

CHUNK = 250_000


class ArquivoIndisponivel(Exception):
    pass


class ColunasNaoEncontradas(Exception):
    pass


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def log(msg: str) -> None:
    print(msg, flush=True)


def aviso(msg: str) -> None:
    print(f"  [aviso] {msg}", file=sys.stderr, flush=True)


def normalizar_texto(s: object) -> str:
    """MAIÚSCULAS, sem acento, sem espaços duplicados."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.upper().split())


def mapear_colunas(colunas: list[str], aliases: dict[str, list[str]], obrigatorias: list[str]) -> dict[str, str]:
    """Retorna {nome_padrao: nome_real_no_arquivo}. Levanta erro se faltar obrigatória."""
    por_nome = {c.strip().strip('"').upper(): c for c in colunas}
    mapa: dict[str, str] = {}
    for chave, opcoes in aliases.items():
        for op in opcoes:
            if op in por_nome:
                mapa[chave] = por_nome[op]
                break
    faltando = [k for k in obrigatorias if k not in mapa]
    if faltando:
        raise ColunasNaoEncontradas(
            f"Não achei colunas para {faltando}. Colunas do arquivo: {list(colunas)}"
        )
    return mapa


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #

def baixar(url: str, destino: Path, forcar: bool = False, offline: bool = False) -> Path:
    if destino.exists() and not forcar:
        log(f"  usando cache: {destino}")
        return destino
    if offline:
        raise ArquivoIndisponivel(f"{destino.name} não está em {destino.parent} (modo --offline)")

    destino.parent.mkdir(parents=True, exist_ok=True)
    log(f"  baixando {url}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (sassamaru-eleicoes; +fetch_tse.py)"})
    tmp = destino.with_suffix(destino.suffix + ".part")
    try:
        with urlopen(req, timeout=120) as resp, open(tmp, "wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            lidos = 0
            while True:
                bloco = resp.read(1 << 20)
                if not bloco:
                    break
                f.write(bloco)
                lidos += len(bloco)
                if total:
                    print(f"\r    {lidos / 1e6:6.1f} / {total / 1e6:.1f} MB", end="", flush=True)
                else:
                    print(f"\r    {lidos / 1e6:6.1f} MB", end="", flush=True)
            print()
    except HTTPError as e:
        tmp.unlink(missing_ok=True)
        raise ArquivoIndisponivel(f"HTTP {e.code} ao baixar {url}") from e
    except (URLError, TimeoutError, OSError) as e:
        tmp.unlink(missing_ok=True)
        raise ArquivoIndisponivel(f"Falha de rede ao baixar {url}: {e}") from e

    if not zipfile.is_zipfile(tmp):
        tmp.unlink(missing_ok=True)
        raise ArquivoIndisponivel(f"O arquivo baixado de {url} não é um zip válido")
    tmp.replace(destino)
    return destino


# --------------------------------------------------------------------------- #
# Leitura dos zips
# --------------------------------------------------------------------------- #

def listar_csvs(zf: zipfile.ZipFile) -> list[str]:
    """Prefere o arquivo nacional (_BRASIL / _BR). Senão, lê todos os CSV/TXT do zip."""
    nomes = [
        n for n in zf.namelist()
        if n.lower().endswith((".csv", ".txt"))
        and "leiame" not in n.lower()
        and "layout" not in n.lower()
    ]
    # _BR (só presidente) e _BRASIL (todos os cargos) repetem as linhas de presidente: ler só um.
    for sufixo in ("_BR", "_BRASIL"):
        nacional = [n for n in nomes if Path(n).stem.upper().endswith(sufixo)]
        if nacional:
            return nacional
    return nomes


def ler_zip(zip_path: Path, aliases: dict, obrigatorias: list[str], encoding: str = "latin-1") -> pd.DataFrame:
    """Lê os CSVs do zip em chunks, mantém só linhas de PRESIDENTE e colunas úteis."""
    partes: list[pd.DataFrame] = []
    with zipfile.ZipFile(zip_path) as zf:
        for nome in listar_csvs(zf):
            with zf.open(nome) as f:
                cab = pd.read_csv(f, sep=";", encoding=encoding, nrows=0, dtype=str)
            mapa = mapear_colunas(list(cab.columns), aliases, obrigatorias)
            inverso = {v: k for k, v in mapa.items()}
            with zf.open(nome) as f:
                leitor = pd.read_csv(
                    f, sep=";", encoding=encoding, dtype=str,
                    usecols=list(mapa.values()), chunksize=CHUNK,
                )
                for chunk in leitor:
                    chunk = chunk.rename(columns=inverso)
                    chunk = chunk[chunk["cargo"].map(normalizar_texto) == "PRESIDENTE"]
                    if len(chunk):
                        partes.append(chunk)
    if not partes:
        return pd.DataFrame(columns=list(aliases))
    return pd.concat(partes, ignore_index=True)


# --------------------------------------------------------------------------- #
# Processamento
# --------------------------------------------------------------------------- #

def agregar_candidatos(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Soma votos por (turno, UF, município, candidato)."""
    df = df.copy()
    for col in ("partido", "nome"):
        if col not in df.columns:
            df[col] = ""
    df["votos"] = pd.to_numeric(df["votos"], errors="coerce").fillna(0)
    df["turno"] = pd.to_numeric(df["turno"], errors="coerce").astype(int)
    for col in ("uf", "cod_municipio", "municipio", "numero", "partido", "nome"):
        df[col] = df[col].astype(str).str.strip()
    df["cod_municipio"] = df["cod_municipio"].str.zfill(5)  # alguns anos vêm sem zero à esquerda

    if "zona" in df.columns:
        dup = df.duplicated(["turno", "uf", "cod_municipio", "zona", "numero"]).sum()
        if dup:
            aviso(f"{ano}: {dup} linhas duplicadas por (turno, município, zona, candidato). "
                  "Se o total nacional divergir, pode haver dupla contagem.")

    chaves = ["turno", "uf", "cod_municipio", "municipio", "numero", "partido", "nome"]
    g = df.groupby(chaves, as_index=False)["votos"].sum()
    g.insert(0, "ano", ano)
    return g


def definir_blocos(cand: pd.DataFrame, override_antipt: dict[int, int] | None = None) -> pd.DataFrame:
    """Adiciona coluna 'bloco' (pt / antipt / outros)."""
    override_antipt = override_antipt or {}
    cand = cand.copy()
    cand["bloco"] = "outros"
    for ano, g in cand.groupby("ano"):
        pt = set(g.loc[g["partido"].str.upper() == "PT", "numero"])
        if not pt:
            aviso(f"{ano}: nenhum candidato com partido 'PT' encontrado; assumindo número 13.")
            pt = {"13"}
        if ano in override_antipt:
            anti = {str(override_antipt[ano])}
        else:
            t2 = g[g["turno"] == 2]
            anti = set(t2.loc[~t2["numero"].isin(pt), "numero"])
        if len(anti) != 1:
            aviso(f"{ano}: adversário do PT no 2º turno ambíguo/ausente ({sorted(anti)}). "
                  "Use ANTIPT_OVERRIDE para definir.")
        mask_ano = cand["ano"] == ano
        cand.loc[mask_ano & cand["numero"].isin(pt), "bloco"] = "pt"
        cand.loc[mask_ano & cand["numero"].isin(anti), "bloco"] = "antipt"
    return cand


def adicionar_pct(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    v = df["validos"].where(df["validos"] > 0)
    d = (df["votos_pt"] + df["votos_antipt"]).where((df["votos_pt"] + df["votos_antipt"]) > 0)
    df["pct_pt_validos"] = 100 * df["votos_pt"] / v
    df["pct_antipt_validos"] = 100 * df["votos_antipt"] / v
    df["pct_outros_validos"] = 100 * df["votos_outros"] / v
    df["pct_pt_dois"] = 100 * df["votos_pt"] / d  # PT / (PT + anti-PT)
    return df.round(4)


def montar_municipios(cand: pd.DataFrame) -> pd.DataFrame:
    chaves = ["ano", "turno", "uf", "cod_municipio", "municipio"]
    g = cand.groupby(chaves + ["bloco"], as_index=False)["votos"].sum()
    w = g.pivot_table(index=chaves, columns="bloco", values="votos", aggfunc="sum", fill_value=0).reset_index()
    w.columns.name = None
    for b in ("pt", "antipt", "outros"):
        if b not in w.columns:
            w[b] = 0
    w = w.rename(columns={"pt": "votos_pt", "antipt": "votos_antipt", "outros": "votos_outros"})
    w["validos"] = w["votos_pt"] + w["votos_antipt"] + w["votos_outros"]
    return w


def agregar_detalhe(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    df = df.copy()
    df["turno"] = pd.to_numeric(df["turno"], errors="coerce").astype(int)
    for col in ("uf", "cod_municipio"):
        df[col] = df[col].astype(str).str.strip()
    df["cod_municipio"] = df["cod_municipio"].str.zfill(5)
    cols = ["aptos", "comparecimento", "brancos", "nulos"]
    for c in cols:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    g = df.groupby(["turno", "uf", "cod_municipio"], as_index=False)[cols].sum()
    g.insert(0, "ano", ano)
    return g


def marcar_capitais(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    norm = df["municipio"].map(normalizar_texto)
    df["eh_capital"] = [CAPITAIS.get(uf) == nm for uf, nm in zip(df["uf"], norm)]
    return df


COLS_CONTAGEM = ["votos_pt", "votos_antipt", "votos_outros", "validos",
                 "aptos", "comparecimento", "brancos", "nulos"]


def agregar_nivel(mun: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    cols = [c for c in COLS_CONTAGEM if c in mun.columns]
    g = mun.groupby(chaves, as_index=False)[cols].sum(min_count=1)
    return adicionar_pct(g)


# --------------------------------------------------------------------------- #
# Verificação contra o resultado oficial
# --------------------------------------------------------------------------- #

def verificar(nacional: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for _, r in nacional.iterrows():
        ref = OFICIAL_PT.get((int(r["ano"]), int(r["turno"])))
        if ref is None:
            continue
        dif = r["pct_pt_validos"] - ref
        linhas.append({
            "ano": int(r["ano"]), "turno": int(r["turno"]),
            "pt_calculado": round(r["pct_pt_validos"], 2), "pt_oficial": ref,
            "diferenca_pp": round(dif, 2),
            "status": "OK" if abs(dif) <= TOLERANCIA_PP else "DIVERGE",
        })
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #

def processar_ano(ano: int, cache: Path, args) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    log(f"\n=== {ano} ===")
    zip_cand = baixar(URL_CANDIDATO.format(ano=ano), cache / f"votacao_candidato_munzona_{ano}.zip",
                      forcar=args.forcar, offline=args.offline)
    bruto = ler_zip(zip_cand, ALIASES_CANDIDATO, OBRIGATORIAS_CANDIDATO, args.encoding)
    if bruto.empty:
        raise ColunasNaoEncontradas(f"{ano}: nenhuma linha de PRESIDENTE encontrada em {zip_cand.name}")
    cand = agregar_candidatos(bruto, ano)
    log(f"  candidatos: {cand['numero'].nunique()} | municípios: {cand['cod_municipio'].nunique()} "
        f"| turnos: {[int(t) for t in sorted(cand['turno'].unique())]}")

    detalhe = None
    if not args.sem_detalhe:
        try:
            zip_det = baixar(URL_DETALHE.format(ano=ano), cache / f"detalhe_votacao_munzona_{ano}.zip",
                             forcar=args.forcar, offline=args.offline)
            det_bruto = ler_zip(zip_det, ALIASES_DETALHE, OBRIGATORIAS_DETALHE, args.encoding)
            detalhe = agregar_detalhe(det_bruto, ano) if not det_bruto.empty else None
        except (ArquivoIndisponivel, ColunasNaoEncontradas) as e:
            aviso(f"{ano}: sem detalhe (aptos/brancos/nulos): {e}")
    return cand, detalhe


def inspecionar(ano: int, cache: Path, args) -> None:
    zip_cand = baixar(URL_CANDIDATO.format(ano=ano), cache / f"votacao_candidato_munzona_{ano}.zip",
                      forcar=args.forcar, offline=args.offline)
    with zipfile.ZipFile(zip_cand) as zf:
        log(f"\nArquivos no zip ({len(zf.namelist())}):")
        for n in zf.namelist()[:40]:
            log(f"  - {n}")
        escolhidos = listar_csvs(zf)
        log(f"\nO script leria: {escolhidos}")
        alvo = escolhidos[0]
        with zf.open(alvo) as f:
            amostra = pd.read_csv(f, sep=";", encoding=args.encoding, dtype=str, nrows=5)
    log(f"\nColunas de {alvo}:")
    for c in amostra.columns:
        log(f"  {c}")
    try:
        mapa = mapear_colunas(list(amostra.columns), ALIASES_CANDIDATO, OBRIGATORIAS_CANDIDATO)
        log(f"\nMapeamento OK: {mapa}")
    except ColunasNaoEncontradas as e:
        log(f"\nMAPEAMENTO FALHOU: {e}\nAjuste ALIASES_CANDIDATO em fetch_tse.py.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Baixa votação para presidente do TSE e salva CSVs.")
    p.add_argument("--anos", type=int, nargs="+", default=ANOS_PADRAO, help="anos de eleição (padrão: 2002–2022)")
    p.add_argument("--saida", type=Path, default=Path("datasets"), help="pasta de saída dos CSVs")
    p.add_argument("--cache", type=Path, default=None, help="pasta dos zips (padrão: <saida>/tse_raw)")
    p.add_argument("--sem-detalhe", action="store_true", help="não baixa aptos/comparecimento/brancos/nulos")
    p.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se já estiver no cache")
    p.add_argument("--offline", action="store_true", help="não acessa a rede; usa só o cache")
    p.add_argument("--encoding", default="latin-1", help="encoding dos CSVs do TSE (padrão: latin-1)")
    p.add_argument("--inspecionar", type=int, metavar="ANO", help="mostra arquivos/colunas do zip e sai")
    args = p.parse_args(argv)

    cache = args.cache or (args.saida / "tse_raw")

    if args.inspecionar:
        try:
            inspecionar(args.inspecionar, cache, args)
        except ArquivoIndisponivel as e:
            log(f"ERRO: {e}")
            return 1
        return 0

    cands, dets, falhas = [], [], []
    for ano in args.anos:
        try:
            c, d = processar_ano(ano, cache, args)
            cands.append(c)
            if d is not None:
                dets.append(d)
        except (ArquivoIndisponivel, ColunasNaoEncontradas) as e:
            falhas.append(ano)
            log(f"  ERRO em {ano}: {e}")

    if not cands:
        log("\nNenhum ano processado. Veja as mensagens acima (use --inspecionar ANO para depurar).")
        return 1

    cand = definir_blocos(pd.concat(cands, ignore_index=True), ANTIPT_OVERRIDE)
    mun = montar_municipios(cand)

    if dets:
        det = pd.concat(dets, ignore_index=True)
        mun = mun.merge(det, on=["ano", "turno", "uf", "cod_municipio"], how="left")
        mun["abstencoes"] = mun["aptos"] - mun["comparecimento"]
    mun = marcar_capitais(adicionar_pct(mun))
    mun = mun.sort_values(["ano", "turno", "uf", "municipio"]).reset_index(drop=True)

    uf = agregar_nivel(mun, ["ano", "turno", "uf"])
    nac = agregar_nivel(mun, ["ano", "turno"])
    cap = mun[mun["eh_capital"]].reset_index(drop=True)

    args.saida.mkdir(parents=True, exist_ok=True)
    arquivos = {
        "tse-presidente-municipio.csv": mun,
        "tse-presidente-uf.csv": uf,
        "tse-presidente-capitais.csv": cap,
        "tse-presidente-nacional.csv": nac,
    }
    log("\n=== Salvando ===")
    for nome, df in arquivos.items():
        caminho = args.saida / nome
        df.to_csv(caminho, index=False, encoding="utf-8")
        log(f"  {caminho}  ({len(df)} linhas)")

    log("\n=== Verificação contra o resultado oficial (% PT nos votos válidos) ===")
    ver = verificar(nac)
    log(ver.to_string(index=False) if len(ver) else "  (sem referência para os anos processados)")
    n_cap = cap.groupby(["ano", "turno"]).size().unique()
    if len(n_cap) and not (set(n_cap) <= {27}):
        aviso(f"Capitais por (ano, turno): {sorted(int(n) for n in n_cap)} (esperado 27). "
              "Pode haver diferença de grafia no nome do município.")
    if falhas:
        log(f"\nAnos com falha: {falhas}")
    if len(ver) and (ver["status"] != "OK").any():
        log("\nATENÇÃO: há divergência com o oficial. Revise blocos/colunas antes de modelar.")
        return 2
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
