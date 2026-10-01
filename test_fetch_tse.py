"""
Testes do fetch_tse.py com dados sintéticos (não usa a rede).

    python -m unittest tests/test_fetch_tse.py -v
"""
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fetch_tse as ft  # noqa: E402


def csv_bytes(linhas, colunas):
    """Gera CSV no formato do TSE: ';' , aspas, latin-1."""
    buf = io.StringIO()
    buf.write(";".join(f'"{c}"' for c in colunas) + "\n")
    for l in linhas:
        buf.write(";".join(f'"{v}"' for v in l) + "\n")
    return buf.getvalue().encode("latin-1")


def zip_com(destino: Path, arquivos: dict):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w") as zf:
        for nome, dados in arquivos.items():
            zf.writestr(nome, dados)


# ---- layout "novo" (2014+) ------------------------------------------------- #
COLS_NOVO = ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA",
             "DS_CARGO", "NR_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "QT_VOTOS_NOMINAIS"]


def linhas_novo():
    L = []
    # 1º turno: Porto Alegre (2 zonas) e Canoas
    for turno, mult in ((1, 1), (2, 1)):
        for zona in ("1", "2"):
            L.append([2022, turno, "RS", "88013", "PORTO ALEGRE", zona, "Presidente", "13", "LULA", "PT", 100 * mult])
            L.append([2022, turno, "RS", "88013", "PORTO ALEGRE", zona, "Presidente", "22", "BOLSONARO", "PL", 80 * mult])
        L.append([2022, turno, "RS", "87912", "CANOAS", "3", "Presidente", "13", "LULA", "PT", 50])
        L.append([2022, turno, "RS", "87912", "CANOAS", "3", "Presidente", "22", "BOLSONARO", "PL", 70])
    # só 1º turno tem terceira via
    L.append([2022, 1, "RS", "88013", "PORTO ALEGRE", "1", "Presidente", "12", "CIRO", "PDT", 20])
    # cargo que deve ser ignorado
    L.append([2022, 1, "RS", "88013", "PORTO ALEGRE", "1", "Governador", "13", "ALGUEM", "PT", 9999])
    return L


# ---- layout "antigo" (2002–2010) ------------------------------------------ #
COLS_ANTIGO = ["NUM_TURNO", "SIGLA_UF", "CODIGO_MUNICIPIO", "NOME_MUNICIPIO", "DESCRICAO_CARGO",
               "NUMERO_CANDIDATO", "NOME_URNA_CANDIDATO", "SIGLA_PARTIDO", "TOTAL_VOTOS"]


def linhas_antigo():
    L = []
    for turno in (1, 2):
        L.append([turno, "SP", "71072", "SÃO PAULO", "PRESIDENTE", "13", "LULA", "PT", 600])
        L.append([turno, "SP", "71072", "SÃO PAULO", "PRESIDENTE", "45", "SERRA", "PSDB", 300])
    L.append([1, "SP", "71072", "SÃO PAULO", "PRESIDENTE", "40", "GAROTINHO", "PSB", 100])
    L.append([1, "SP", "71072", "SÃO PAULO", "DEPUTADO FEDERAL", "1313", "OUTRO", "PT", 5000])
    return L


COLS_DET = ["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "DS_CARGO", "QT_APTOS", "QT_COMPARECIMENTO",
            "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS"]


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cache = self.tmp / "tse_raw"

        # 2022: arquivo _BRASIL (usado) + arquivo de UF com as mesmas linhas (deve ser ignorado)
        brasil = csv_bytes(linhas_novo(), COLS_NOVO)
        zip_com(self.cache / "votacao_candidato_munzona_2022.zip", {
            "votacao_candidato_munzona_2022_BRASIL.csv": brasil,
            "votacao_candidato_munzona_2022_RS.csv": brasil,
            "leiame.pdf": b"%PDF",
        })
        det = [[t, "RS", "88013", "Presidente", 1000, 900, 10, 20] for t in (1, 2)]
        det += [[t, "RS", "87912", "Presidente", 500, 400, 5, 5] for t in (1, 2)]
        zip_com(self.cache / "detalhe_votacao_munzona_2022.zip", {
            "detalhe_votacao_munzona_2022_BRASIL.csv": csv_bytes(det, COLS_DET),
        })

        # 2002: layout antigo, sem arquivo nacional, sem detalhe
        zip_com(self.cache / "votacao_candidato_munzona_2002.zip", {
            "votacao_candidato_munzona_2002_SP.txt": csv_bytes(linhas_antigo(), COLS_ANTIGO),
        })

    # -- unidades ------------------------------------------------------------ #
    def test_normalizar_texto(self):
        self.assertEqual(ft.normalizar_texto("  São  Luís "), "SAO LUIS")

    def test_mapear_colunas_erro_mostra_colunas(self):
        with self.assertRaises(ft.ColunasNaoEncontradas) as cm:
            ft.mapear_colunas(["A", "B"], ft.ALIASES_CANDIDATO, ft.OBRIGATORIAS_CANDIDATO)
        self.assertIn("['A', 'B']", str(cm.exception))

    def test_listar_csvs_prefere_nacional(self):
        with zipfile.ZipFile(self.cache / "votacao_candidato_munzona_2022.zip") as zf:
            self.assertEqual(ft.listar_csvs(zf), ["votacao_candidato_munzona_2022_BRASIL.csv"])

    def test_ler_zip_filtra_presidente_e_layout_antigo(self):
        df = ft.ler_zip(self.cache / "votacao_candidato_munzona_2002.zip",
                        ft.ALIASES_CANDIDATO, ft.OBRIGATORIAS_CANDIDATO)
        self.assertEqual(set(df["cargo"].str.upper()), {"PRESIDENTE"})
        self.assertEqual(len(df), 5)
        self.assertIn("SÃO PAULO", set(df["municipio"]))  # latin-1 decodificado

    def test_blocos_e_antipt_via_segundo_turno(self):
        bruto = ft.ler_zip(self.cache / "votacao_candidato_munzona_2022.zip",
                           ft.ALIASES_CANDIDATO, ft.OBRIGATORIAS_CANDIDATO)
        cand = ft.definir_blocos(ft.agregar_candidatos(bruto, 2022))
        mapa = cand.drop_duplicates("numero").set_index("numero")["bloco"].to_dict()
        self.assertEqual(mapa, {"13": "pt", "22": "antipt", "12": "outros"})

    def test_uf_nao_dobra_contagem_com_arquivo_de_uf(self):
        rc = ft.main(["--saida", str(self.tmp / "out"), "--cache", str(self.cache),
                      "--offline", "--anos", "2022"])
        uf = pd.read_csv(self.tmp / "out" / "tse-presidente-uf.csv")
        t1 = uf[(uf.ano == 2022) & (uf.turno == 1)].iloc[0]
        # PT: 100*2 (POA) + 50 (Canoas) = 250; anti: 80*2 + 70 = 230; outros: 20
        self.assertEqual((t1.votos_pt, t1.votos_antipt, t1.votos_outros, t1.validos), (250, 230, 20, 500))
        self.assertEqual(t1.aptos, 1500)
        self.assertEqual(t1.brancos, 15)
        self.assertEqual(rc, 2)  # números sintéticos divergem do oficial → código 2

    # -- fim a fim ----------------------------------------------------------- #
    def test_main_completo_dois_layouts(self):
        out = self.tmp / "out"
        rc = ft.main(["--saida", str(out), "--cache", str(self.cache), "--offline"])
        mun = pd.read_csv(out / "tse-presidente-municipio.csv", dtype={"cod_municipio": str})
        self.assertEqual(set(mun.ano), {2002, 2022})
        self.assertEqual(rc, 2)

        poa = mun[(mun.ano == 2022) & (mun.turno == 2) & (mun.municipio == "PORTO ALEGRE")].iloc[0]
        self.assertTrue(poa.eh_capital)
        self.assertEqual(poa.votos_pt, 200)
        self.assertAlmostEqual(poa.pct_pt_dois, 100 * 200 / 360, places=3)
        self.assertFalse(mun[mun.municipio == "CANOAS"].eh_capital.any())

        sp = mun[(mun.ano == 2002) & (mun.turno == 1)].iloc[0]
        self.assertTrue(sp.eh_capital)
        self.assertEqual((sp.votos_pt, sp.votos_antipt, sp.votos_outros), (600, 300, 100))
        self.assertTrue(pd.isna(sp.aptos))  # 2002 sem detalhe → vazio, não zero

        caps = pd.read_csv(out / "tse-presidente-capitais.csv")
        self.assertTrue(caps.eh_capital.all())

    def test_ano_sem_arquivo_em_offline_falha_com_mensagem(self):
        rc = ft.main(["--saida", str(self.tmp / "out2"), "--cache", str(self.cache),
                      "--offline", "--anos", "2010"])
        self.assertEqual(rc, 1)

    def test_verificar_ok_quando_bate(self):
        nac = pd.DataFrame([{"ano": 2022, "turno": 2, "pct_pt_validos": 50.90}])
        self.assertEqual(ft.verificar(nac).iloc[0].status, "OK")
        nac = pd.DataFrame([{"ano": 2022, "turno": 2, "pct_pt_validos": 49.0}])
        self.assertEqual(ft.verificar(nac).iloc[0].status, "DIVERGE")


if __name__ == "__main__":
    unittest.main()
