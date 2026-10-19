"""Quanto um classificador automático acerta a posição de um post do Bluesky sobre o candidato que ele cita? (não altera nada do modelo eleitoral)

Gabarito = rótulos de uma amostra de 304 posts que citam só Lula ou só Flávio (datasets/redes/rotulos-amostra.csv): P (favorável ao candidato citado),
N (desfavorável) ou 0 (neutro, notícia, piada ou posição não expressa). Os rótulos são do Claude (leitura de cada post); não há segundo anotador, então a
concordância entre pessoas não foi medida. Os textos ficam só no cache local (datasets/redes/bluesky-bruto.jsonl, fora do git).
Compara: três modelos prontos (sentimento multilíngue, sentimento de tweets, NLI zero-shot), uma regressão logística em TF-IDF (validação cruzada 5×5)
e uma linha de base trivial: "Lula = favorável, Flávio = desfavorável". Grava datasets/redes/avaliacao-modelos.json.
  pip install torch transformers scikit-learn sentencepiece tiktoken     # só para este script
  python avaliar_sentimento_redes.py"""
import json
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
D = "datasets/redes/"
rot = pd.read_csv(D + "rotulos-amostra.csv")
bruto = {}
for l in open(D + "bluesky-bruto.jsonl", encoding="utf-8"):
    r = json.loads(l)
    bruto[r["id"]] = r["texto"]
s = rot[rot.id.isin(bruto)].copy()
s["texto"] = s.id.map(bruto)
print("rotulados com texto no cache:", len(s), "de", len(rot))
res = {"n": int(len(s)), "rotulos": s.rotulo.value_counts().to_dict(), "modelos": []}


def registrar(nome, descr, pred, extra=None):
    acc = float((pred == s.rotulo.to_numpy()).mean())
    d = dict(nome=nome, descricao=descr, acuracia=round(acc, 3), **(extra or {}))
    res["modelos"].append(d)
    print(f"{nome:34s} {acc:.3f}")


# linha de base: a posição é decidida só por quem é citado
base = np.where(s.cand == "lula", "P", "N")
registrar("Linha de base (Lula = favorável, Flávio = desfavorável)", "Não olha o texto: só quem é citado.", base)

from transformers import pipeline   # noqa: E402


def pronto(nome, descr, modelo, mapa):
    t = time.time()
    p = pipeline("text-classification", model=modelo, top_k=None, truncation=True, max_length=256)
    out = p(s.texto.tolist(), batch_size=16)
    pred = np.array([mapa[max(o, key=lambda x: x["score"])["label"].lower()] for o in out])
    registrar(nome, descr, pred, {"segundos": round(time.time() - t)})


pronto("Sentimento multilíngue (DistilBERT)", "lxyuan/distilbert-base-multilingual-cased-sentiments-student", "lxyuan/distilbert-base-multilingual-cased-sentiments-student",
       {"positive": "P", "negative": "N", "neutral": "0"})
pronto("Sentimento de tweets (XLM-R)", "cardiffnlp/twitter-xlm-roberta-base-sentiment", "cardiffnlp/twitter-xlm-roberta-base-sentiment",
       {"positive": "P", "negative": "N", "neutral": "0", "label_0": "N", "label_1": "0", "label_2": "P"})

t = time.time()
zs = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
nome = {"lula": "Lula", "flavio": "Flávio Bolsonaro"}
pred = []
for r in s.itertuples():
    c = nome[r.cand]
    labs = [f"o autor apoia ou elogia {c}", f"o autor critica ou ataca {c}", f"o autor apenas informa ou comenta sobre {c}"]
    o = zs(r.texto[:400], candidate_labels=labs, hypothesis_template="{}.", multi_label=False)
    pred.append({0: "P", 1: "N", 2: "0"}[labs.index(o["labels"][0])])
registrar("Posição por NLI zero-shot (mDeBERTa)", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli, três hipóteses por candidato", np.array(pred), {"segundos": round(time.time() - t)})

from sklearn.feature_extraction.text import TfidfVectorizer   # noqa: E402
from sklearn.linear_model import LogisticRegression   # noqa: E402
from sklearn.model_selection import StratifiedKFold, cross_val_predict   # noqa: E402
from sklearn.pipeline import make_pipeline, make_union   # noqa: E402

X, y = s.cand + " " + s.texto.str.lower(), s.rotulo
vec = make_union(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True))
clf = make_pipeline(vec, LogisticRegression(C=10, max_iter=2000, class_weight="balanced"))
accs = [(cross_val_predict(clf, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=k)) == y).mean() for k in range(5)]
d = dict(nome="Regressão logística em TF-IDF (validação cruzada)", descricao="Palavras e trechos de letras + quem é citado; 5 partições × 5 repetições",
         acuracia=round(float(np.mean(accs)), 3), desvio=round(float(np.std(accs)), 3))
res["modelos"].append(d)
print(f"{d['nome']:34s} {d['acuracia']:.3f} ± {d['desvio']:.3f}")

# por candidato, quem é favorável/desfavorável (a base do argumento)
res["por_candidato"] = {c: s[s.cand == c].rotulo.value_counts().to_dict() for c in ("lula", "flavio")}
json.dump(res, open(D + "avaliacao-modelos.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("grava", D + "avaliacao-modelos.json")
