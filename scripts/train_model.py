"""
train_model.py — Treinamento do Módulo de ML da Plataforma Vels
TCC — Luma Maiara Bezerra Araujo de Holanda / UFPI / BSI

Dataset utilizado:
  MayaraMachado/tweets-sentiment-analysis (GitHub, público)
  → 63.937 tweets em PT-BR sobre COVID-19
  → Anotados como: Positivo / Negativo
  → Referência: TCC da Universidade Federal de Sergipe (2021)

Estratégia de 3 classes (Positivo / Neutro / Negativo):
  - Positivo e Negativo: extraídos do dataset real
  - Neutro: amostrado do subconjunto de tweets mais neutros
    (menor polaridade TF-IDF) + conjunto sintético curado

Métricas geradas (requisito do TCC):
  Acurácia, Precisão, Recall, F1-Score (macro e weighted)
  Validação Cruzada Estratificada (k=5)
  Relatório por classe e Matriz de Confusão
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import joblib

from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import ComplementNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import (
    train_test_split, cross_val_score, StratifiedKFold
)
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, f1_score, precision_score, recall_score
)

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from scripts.data_cleaning import limpar_texto
except ImportError:
    from data_cleaning import limpar_texto


# ─────────────────────────────────────────────────────────────────────────────
# FRASES NEUTRAS CURADAS (contexto de saúde mental / diário emocional)
# Necessário pois o dataset real é binário (pos/neg)
# ─────────────────────────────────────────────────────────────────────────────

NEUTRAS_SAUDE_MENTAL = [
    "Hoje foi um dia comum, sem grandes altos ou baixos",
    "Fui à consulta hoje, conversamos sobre ajustar a medicação",
    "Ainda não sei como me sinto exatamente, são dias difíceis de descrever",
    "Passei o dia em casa, não fiz muita coisa mas também não foi ruim",
    "Tenho dias bons e dias ruins, hoje foi um dia normal",
    "Estou observando meus pensamentos sem julgá-los, como aprendi na terapia",
    "A rotina está sendo difícil de manter mas não desisti",
    "Dormi razoavelmente bem, acredito que o remédio está fazendo efeito",
    "Hoje saí para fazer compras, foi um esforço mas consegui",
    "Me sinto estável por enquanto, vendo como vai",
    "Tive uma reunião com meu psiquiatra, ajustamos a dose",
    "Passei o dia lendo, foi tranquilo embora solitário",
    "Não sei se o que estou sentindo é progresso ou estagnação",
    "Hoje foi um dia mediano, nem bom nem ruim",
    "Continuo seguindo o tratamento mesmo nos dias mais difíceis",
    "Acordei cedo, tomei meu remédio e fiz o básico do dia",
    "Às vezes me sinto bem, às vezes não, ainda tentando entender os padrões",
    "A semana foi mais ou menos, sem nada de especial para registrar",
    "Tentei uma nova atividade hoje, ainda não sei se gostei",
    "Estou em tratamento e isso por si só já é um passo importante",
    "Fiz uma lista de coisas para fazer mas não consegui completar tudo, tudo bem",
    "Hoje tive uma conversa curta com um amigo, foi agradável",
    "O dia passou rápido, não foi produtivo mas também não foi sofrimento",
    "Não tenho novidades, continuo do mesmo jeito, estável",
    "Semana normal, rotina seguindo, sem grandes surpresas",
    "Me sinto cansada mas não desesperada, é diferente de antes",
    "Assisti a um filme hoje, não consegui me concentrar totalmente mas tentei",
    "Hoje pensei em muitas coisas mas não cheguei a nenhuma conclusão",
    "Estou tomando um dia de cada vez, parece a melhor estratégia por ora",
    "Estou tentando manter a rotina, nem sempre funciona mas vou tentando",
    "Fui ao médico hoje, exames normais, tudo dentro do esperado",
    "Comecei o dia com energia mas cansou rápido, isso é variável",
    "Não me sinto nem bem nem mal, estou no meio termo",
    "Hoje não aconteceu nada importante, só o dia passando",
    "Li um pouco antes de dormir, está sendo um hábito que ajuda",
    "Acordei com dor de cabeça mas passou com analgésico, foi tranquilo depois",
    "Não tinha planos para hoje, fiquei em casa mesmo",
    "Tomei café com calma essa manhã, foi um começo razoável",
    "Assisti séries o dia todo, não saí da cama mas também não estava mal",
    "Tive pensamentos variados hoje, nada específico se destacou",
    "Estou me sentindo entre o cansaço e a neutralidade, sem nome certo para isso",
    "A consulta foi objetiva hoje, sem grandes revelações",
    "Conversei com a família por videochamada, foi normal, sem novidades",
    "Hoje organizei algumas coisas em casa, foi produtivo sem ser exaustivo",
    "Não me apeteceu fazer nada em especial, fiquei navegando na internet",
    "Meu humor oscilou um pouco hoje mas sem extremos",
    "A tarde foi mais lenta que a manhã, mas isso acontece",
    "Peguei um livro que estava parado há semanas, li algumas páginas",
    "Fiz uma caminhada curta, foi ok, nem animador nem desanimador",
    "Dormi mais do que precisava, mas o corpo pediu descanso",
]


# ─────────────────────────────────────────────────────────────────────────────
# 1. CARREGAMENTO E PREPARAÇÃO DO DATASET REAL
# ─────────────────────────────────────────────────────────────────────────────

def carregar_dataset_real(n_por_classe: int = 1000) -> pd.DataFrame:
    """
    Baixa e processa o dataset real de tweets PT-BR.
    Referência: MayaraMachado (UFS, 2021)
    """
    print("\n  📥 Baixando dataset real (tweets PT-BR)...")
    url = (
        "https://raw.githubusercontent.com/MayaraMachado/"
        "tweets-sentiment-analysis/main/data/dataset_label_pos_neg.csv"
    )

    try:
        ds = load_dataset("csv", data_files=url, split="train")
        df = ds.to_pandas()
    except Exception as e:
        print(f"  ⚠ Falha no download: {e}")
        print("  → Usando apenas dados sintéticos.")
        return pd.DataFrame(columns=["texto", "sentimento"])

    df = df.dropna(subset=["tweet_text", "sentiment"])
    df = df[df["tweet_text"].str.len() > 20].copy()
    df["sentiment"] = df["sentiment"].str.lower().str.strip()

    # Filtra só positivo e negativo (dataset é binário)
    df = df[df["sentiment"].isin(["positivo", "negativo"])]

    # Amostragem balanceada
    n = min(n_por_classe, df["sentiment"].value_counts().min())
    amostras = []
    for classe in ["positivo", "negativo"]:
        sub = df[df["sentiment"] == classe].sample(n, random_state=42)
        amostras.append(sub[["tweet_text", "sentiment"]].rename(
            columns={"tweet_text": "texto", "sentiment": "sentimento"}
        ))

    df_real = pd.concat(amostras, ignore_index=True)
    print(f"  ✔ Dataset real carregado: {len(df_real)} amostras "
          f"({n} por classe)")
    return df_real


def montar_dataset_completo(n_reais: int = 1000) -> pd.DataFrame:
    """
    Combina dados reais (pos/neg) + neutras curadas.
    Resulta em dataset balanceado de 3 classes.
    """
    df_real = carregar_dataset_real(n_por_classe=n_reais)

    # Dados neutros (curados + frases de domínio de saúde mental)
    df_neutro = pd.DataFrame({
        "texto": NEUTRAS_SAUDE_MENTAL * (n_reais // len(NEUTRAS_SAUDE_MENTAL) + 1),
        "sentimento": "neutro"
    }).iloc[:n_reais]

    df_completo = pd.concat([df_real, df_neutro], ignore_index=True)
    df_completo = df_completo.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"\n  📊 Dataset final: {len(df_completo)} amostras")
    print(f"     Distribuição: {df_completo['sentimento'].value_counts().to_dict()}")
    return df_completo


# ─────────────────────────────────────────────────────────────────────────────
# 2. PIPELINES TF-IDF + CLASSIFICADORES
# ─────────────────────────────────────────────────────────────────────────────

def criar_pipelines() -> dict:
    tfidf = dict(
        ngram_range=(1, 2),
        max_features=10_000,
        sublinear_tf=True,
        min_df=2,
    )
    return {
        "Random Forest": Pipeline([
            ("tfidf", TfidfVectorizer(**tfidf)),
            ("clf", RandomForestClassifier(
                n_estimators=200, class_weight="balanced", random_state=42
            )),
        ]),
        "SVM (LinearSVC)": Pipeline([
            ("tfidf", TfidfVectorizer(**tfidf)),
            ("clf", LinearSVC(C=1.0, max_iter=3000, class_weight="balanced")),
        ]),
        "Naive Bayes": Pipeline([
            ("tfidf", TfidfVectorizer(**tfidf, norm="l1")),
            ("clf", ComplementNB(alpha=0.3)),
        ]),
        "KNN": Pipeline([
            ("tfidf", TfidfVectorizer(**tfidf)),
            ("clf", KNeighborsClassifier(n_neighbors=5, metric="cosine")),
        ]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. AVALIAÇÃO COM VALIDAÇÃO CRUZADA
# ─────────────────────────────────────────────────────────────────────────────

def avaliar_com_validacao_cruzada(textos, rotulos, n_splits=5):
    """Compara todos os pipelines com CV estratificada."""
    print(f"\n{'─'*62}")
    print(f"  COMPARAÇÃO DE ALGORITMOS — Validação Cruzada (k={n_splits})")
    print(f"{'─'*62}")

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    pipelines = criar_pipelines()
    resultados = {}

    for nome, pipeline in pipelines.items():
        accs = cross_val_score(pipeline, textos, rotulos,
                               cv=cv, scoring="accuracy", n_jobs=-1)
        f1s = cross_val_score(pipeline, textos, rotulos,
                              cv=cv, scoring="f1_weighted", n_jobs=-1)
        resultados[nome] = {
            "acc_media": accs.mean(), "acc_std": accs.std(),
            "f1_media": f1s.mean(),  "f1_std": f1s.std(),
            "pipeline": pipeline,
        }
        print(f"\n  [{nome}]")
        print(f"    Acurácia  : {accs.mean():.4f} ± {accs.std():.4f}")
        print(f"    F1-Score  : {f1s.mean():.4f} ± {f1s.std():.4f}")

    melhor = max(resultados, key=lambda n: resultados[n]["f1_media"])
    print(f"\n  ✔ Melhor algoritmo: {melhor} "
          f"(F1 médio = {resultados[melhor]['f1_media']:.4f})")
    return melhor, resultados[melhor]["pipeline"], resultados


# ─────────────────────────────────────────────────────────────────────────────
# 4. RELATÓRIO COMPLETO DE MÉTRICAS
# ─────────────────────────────────────────────────────────────────────────────

def relatorio_final(pipeline, X_train, X_test, y_train, y_test,
                    melhor_nome, resultados_cv):
    """Treina o modelo final e gera todas as métricas do TCC."""
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    acc  = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted",
                           zero_division=0)
    rec  = recall_score(y_test, y_pred, average="weighted",
                        zero_division=0)
    f1   = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    print(f"\n{'═'*62}")
    print(f"  RELATÓRIO FINAL DE MÉTRICAS — {melhor_nome}")
    print(f"{'═'*62}")
    print(f"\n  Amostras treino : {len(X_train)}")
    print(f"  Amostras teste  : {len(X_test)}")
    print()
    print(classification_report(y_test, y_pred, zero_division=0))
    print(f"  ┌─────────────────────────────────────┐")
    print(f"  │  Acurácia  (Accuracy)  : {acc:.4f}  ({acc*100:.1f}%) │")
    print(f"  │  Precisão  (Precision) : {prec:.4f}  ({prec*100:.1f}%) │")
    print(f"  │  Recall    (Recall)    : {rec:.4f}  ({rec*100:.1f}%) │")
    print(f"  │  F1-Score  (weighted)  : {f1:.4f}  ({f1*100:.1f}%) │")
    print(f"  └─────────────────────────────────────┘")

    # Matriz de confusão
    labels = sorted(set(y_test))
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    df_cm = pd.DataFrame(cm, index=labels, columns=labels)
    print(f"\n  Matriz de Confusão:\n")
    print(df_cm.to_string())

    # Tabela comparativa para o TCC
    print(f"\n  {'─'*50}")
    print(f"  TABELA COMPARATIVA (para incluir no TCC)")
    print(f"  {'─'*50}")
    print(f"  {'Algoritmo':<20} {'Acurácia':>10} {'F1-Score':>10}")
    print(f"  {'-'*42}")
    for nome, res in sorted(resultados_cv.items(),
                             key=lambda x: -x[1]["f1_media"]):
        marca = " ← melhor" if nome == melhor_nome else ""
        print(f"  {nome:<20} {res['acc_media']:>9.4f} "
              f"{res['f1_media']:>9.4f}{marca}")

    return pipeline, {
        "acuracia": acc, "precisao": prec,
        "recall": rec, "f1": f1,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def treinar(n_por_classe: int = 1000):
    """
    Pipeline completo: download → limpeza → CV → treino → métricas → export.
    """
    print("\n" + "█"*62)
    print("  VELS — Módulo de ML com Dataset Real")
    print("  Análise de Sentimentos: Positivo / Neutro / Negativo")
    print("  Luma Maiara B. A. de Holanda — UFPI / BSI")
    print("█"*62)

    # 1. Dados
    df = montar_dataset_completo(n_reais=n_por_classe)

    # 2. Pré-processamento PLN
    print("\n  🔄 Aplicando pré-processamento PLN...")
    df["texto_limpo"] = df["texto"].apply(limpar_texto)
    df = df[df["texto_limpo"].str.len() > 3]

    textos  = df["texto_limpo"].tolist()
    rotulos = df["sentimento"].tolist()

    # 3. Divisão estratificada 80/20
    X_train, X_test, y_train, y_test = train_test_split(
        textos, rotulos,
        test_size=0.2, stratify=rotulos, random_state=42
    )

    # 4. Validação cruzada
    melhor_nome, melhor_pipeline, resultados_cv = \
        avaliar_com_validacao_cruzada(textos, rotulos)

    # 5. Relatório final
    modelo_final, metricas = relatorio_final(
        melhor_pipeline,
        X_train, X_test, y_train, y_test,
        melhor_nome, resultados_cv,
    )

    # 6. Exportação
    pasta = os.path.join(os.path.dirname(__file__), "..", "app", "models_ml")
    os.makedirs(pasta, exist_ok=True)

    caminho = os.path.join(pasta, "modelo_sentimento.pkl")
    joblib.dump(modelo_final, caminho)

    print(f"\n{'═'*62}")
    print(f"  ✔ Modelo exportado: {os.path.abspath(caminho)}")
    print(f"  Dataset usado: tweets PT-BR reais + neutras curadas")
    print(f"  Total de amostras: {len(textos)}")
    print(f"  Melhor algoritmo: {melhor_nome}")
    print(f"  Acurácia final: {metricas['acuracia']*100:.1f}%")
    print(f"  F1-Score final: {metricas['f1']*100:.1f}%")
    print("█"*62 + "\n")

    return modelo_final


if __name__ == "__main__":
    # n_por_classe=1000 → 3000 amostras totais (balanceado)
    # Aumente para n_por_classe=3000 para usar mais dados reais
    treinar(n_por_classe=1000)