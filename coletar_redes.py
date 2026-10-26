"""Coleta posts públicos do Bluesky (busca aberta da API, sem login) sobre Lula e Flávio no 2º turno.

  python coletar_redes.py                 # janelas de 6 h de 12/10 até agora + janelas de 1 h em volta dos debates (Band 18/10 20h-22h; Globo 23/10 21h20-23h30, BRT) e da apuração (25/10 18h a 26/10 6h)
Grava datasets/redes/bluesky-bruto.jsonl (cache LOCAL, fora do git): sem @, sem nome, sem avatar; autor só como hash curto, para contar posts por autor.
O que vai para o git são só os agregados (analisar_redes.py). Posts públicos; a coleta respeita os limites da API (pausa entre chamadas).
ponytail: a busca devolve os posts mais recentes de cada janela, então cada janela é uma amostra (até MAX_PAG páginas), não o total; o Bluesky não é uma amostra do eleitorado."""
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"
BRT = timezone(timedelta(hours=-3))
SAIDA = Path("datasets/redes/bluesky-bruto.jsonl")
VOLUME = Path("datasets/redes/bluesky-volume.csv")      # agregado (vai para o git): total de posts que a busca informa em cada janela e termo
TERMOS = {"lula": ["Lula"], "flavio": ["Flávio Bolsonaro"], "checagem": ["checagem"]}   # "checagem": conversa sobre fact-check (só volume, para o debate da Globo)
MAX_PAG = 1          # páginas de 100 posts por (termo, janela); a busca também informa o total (hitsTotal) de cada janela
DEBATES = [    # (início, fim, horas de janela fina antes, horas depois): o da Globo é o mais esperado (checagem ao vivo), então a janela dele é bem maior
    (datetime(2026, 10, 18, 20, tzinfo=BRT), datetime(2026, 10, 18, 22, tzinfo=BRT), 1, 6),
    (datetime(2026, 10, 23, 21, 20, tzinfo=BRT), datetime(2026, 10, 23, 23, 30, tzinfo=BRT), 3, 12.5),
    (datetime(2026, 10, 25, 18, tzinfo=BRT), datetime(2026, 10, 25, 23, 30, tzinfo=BRT), 0, 6.5),      # apuração do 2º turno e reeleição de Lula (resultado às 21h08): janelas finas de 25/10 18h a 26/10 6h   # janelas finas de 23/10 18h a 24/10 12h (alinhadas à grade de 6 h)
]


def janelas(agora):
    ini = datetime(2026, 10, 12, 0, tzinfo=BRT)
    finas = [((a - timedelta(hours=antes)).replace(minute=0), b + timedelta(hours=depois)) for a, b, antes, depois in DEBATES]
    em_fina = lambda t: any(x <= t < y for x, y in finas)
    out, t = [], ini
    while t < agora:
        fim = min(t + timedelta(hours=6), agora)
        if not em_fina(t):                                        # em volta dos debates: janelas finas
            out.append((t, fim, MAX_PAG))
        t = fim
    for x, y in finas:
        t = x.replace(minute=0)
        while t < min(y, agora):
            out.append((t, min(t + timedelta(hours=1), agora), 2))
            t += timedelta(hours=1)
    return sorted(out)


def buscar(q, ini, fim, cursor=None):
    p = {"q": q, "lang": "pt", "sort": "latest", "limit": 100, "since": ini.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
         "until": fim.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if cursor:
        p["cursor"] = cursor
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(p), headers={"User-Agent": "eleicoes-dashboard-pesquisa/1.0"})
    for tentativa in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=25))
        except Exception as e:                      # 403/429/5xx e quedas do túnel (intermitentes nesta rede): espera um pouco mais a cada tentativa
            time.sleep(2 + tentativa)
            err = e
    print("falhou:", q, ini, err, file=sys.stderr)
    return {"posts": []}


def enxuto(p, cand):
    r, e = p["record"], p.get("embed") or {}
    tem_link = "external" in str(e.get("$type", "")) or any("link" in str(f) for f in r.get("facets", []))
    return dict(id=p["uri"].split("/")[-1] + "-" + hashlib.sha1(p["author"]["did"].encode()).hexdigest()[:6], autor=hashlib.sha1(p["author"]["did"].encode()).hexdigest()[:10],
                criado=p["indexedAt"], texto=r.get("text", ""), likes=p.get("likeCount", 0), reposts=p.get("repostCount", 0), respostas=p.get("replyCount", 0),
                citacoes=p.get("quoteCount", 0), link=bool(tem_link), busca=cand)


def salvar(vistos, volume):
    SAIDA.write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in vistos.values()) + "\n", encoding="utf-8")
    VOLUME.write_text("inicio,fim,candidato,termo,posts\n" + "".join(f"{a},{b},{c},{d},{n}\n" for (a, b, c, d), n in sorted(volume.items())), encoding="utf-8")


def main():
    agora = datetime.now(BRT)
    volume = {}
    if VOLUME.exists():
        for l in VOLUME.read_text(encoding="utf-8").splitlines()[1:]:
            ini_, fim_, cand_, termo_, n_ = l.split(",")
            volume[(ini_, fim_, cand_, termo_)] = int(n_)
    vistos = {}
    if SAIDA.exists():
        for l in SAIDA.read_text(encoding="utf-8").splitlines():
            d = json.loads(l)
            vistos[d["id"]] = d
    novos = 0
    for ini, fim, mp in janelas(agora):
        for cand, qs in TERMOS.items():
            for q in qs:
                if (ini.isoformat(), fim.isoformat(), cand, q) in volume:       # já coletada com sucesso: só refaz o que falhou
                    continue
                cursor = None
                for _ in range(mp):
                    r = buscar(q, ini, fim, cursor)
                    if cursor is None and "hitsTotal" in r:
                        volume[(ini.isoformat(), fim.isoformat(), cand, q)] = int(r["hitsTotal"])
                    for p in r.get("posts", []):
                        d = enxuto(p, cand)
                        if d["id"] not in vistos:
                            vistos[d["id"]] = d
                            novos += 1
                        elif cand not in vistos[d["id"]]["busca"]:
                            vistos[d["id"]]["busca"] += "," + cand
                    cursor = r.get("cursor")
                    time.sleep(0.5)
                    if not cursor:
                        break
        print(ini.strftime("%d/%m %Hh"), "->", len(vistos), "posts", flush=True)
        salvar(vistos, volume)                          # grava a cada janela: se for interrompido, retoma do cache
    salvar(vistos, volume)
    print("novos:", novos, "total:", len(vistos))


if __name__ == "__main__":
    main()
