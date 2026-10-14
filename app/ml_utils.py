"""
ml_utils.py — Motor de Inferência de Machine Learning da Plataforma Vels
TCC — Luma Maiara Bezerra Araujo de Holanda / UFPI / BSI

Este módulo gerencia:
1. Limpeza e pré-processamento de texto em Linguagem Natural (PLN).
2. Carregamento e inferência real do modelo treinado (TfidfVectorizer + Classificador).
3. Detecção proativa e prioritária de risco crítico (salvaguarda de saúde mental e CVV 188).
"""
import os
import re
import warnings
import joblib

# ── Termos Críticos de Risco Alto (Salvaguarda Prioritária de Vida) ─────────────
PALAVRAS_RISCO_ALTO = {
    'suicídio', 'suicidio', 'suicidar', 'me matar', 'quero morrer',
    'não quero mais viver', 'nao quero mais viver', 'acabar com tudo',
    'me machucar', 'me ferir', 'autolesão', 'autolesao', 'me cortar',
    'não vejo saída', 'nao vejo saida', 'desaparecer para sempre',
    'ninguém sentirá minha falta', 'ninguem sentira minha falta',
    'pensei em me matar', 'tentativa de suicídio', 'quero acabar',
    'não quero mais existir', 'nao quero mais existir', 'tirar minha vida',
    'dar um fim na minha vida', 'vontade de sumir e não voltar mais'
}

# ── Termos para fallback léxico caso o modelo não esteja em disco ──────────────
TERMOS_RISCO_FALLBACK = [
    'cansado', 'cansada', 'desamparado', 'desamparada', 'não aguento mais',
    'nao aguento mais', 'triste', 'sozinho', 'sozinha', 'vazio', 'pressão',
    'pressao', 'desistir', 'dor', 'nada muda', 'socorro', 'mal', 'angústia',
    'angustia', 'desespero', 'crise', 'pânico', 'panico', 'choro', 'fracasso'
]

TERMOS_POSITIVOS_FALLBACK = [
    'feliz', 'alegre', 'ótimo', 'ótima', 'otimo', 'otima', 'bem', 'consegui',
    'obrigado', 'obrigada', 'paz', 'leve', 'melhor', 'esperança', 'esperanca',
    'amigas', 'amigos', 'família', 'familia', 'conquista', 'alívio', 'alivio',
    'grato', 'grata', 'gratidão', 'gratidao', 'sorriso', 'calma'
]

_modelo_pipeline = None


def _limpar_texto(texto: str) -> str:
    """
    Pré-processamento de PLN: normalização, remoção de URLs,
    menções, hashtags e caracteres não alfanuméricos.
    """
    if not texto:
        return ""
    texto = texto.lower()
    texto = re.sub(r'http\S+|www\.\S+', ' ', texto)        # remove URLs
    texto = re.sub(r'@\w+', ' ', texto)                   # remove menções
    texto = re.sub(r'#\w+', ' ', texto)                   # remove hashtags
    texto = re.sub(r'[^\w\sáéíóúâêîôûãõç]', ' ', texto)   # mantém letras acentuadas
    texto = re.sub(r'\s+', ' ', texto).strip()            # colapsa múltiplos espaços
    return texto


def _carregar_modelo():
    """
    Carrega o Pipeline de Machine Learning (TF-IDF + Classificador)
    em memória com cache singleton.
    """
    global _modelo_pipeline
    if _modelo_pipeline is not None:
        return _modelo_pipeline

    caminho = os.path.join(
        os.path.dirname(__file__), 'models_ml', 'modelo_sentimento.pkl'
    )
    if os.path.exists(caminho):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                _modelo_pipeline = joblib.load(caminho)
        except Exception as e:
            print(f"[ML_UTILS] Aviso ao carregar modelo: {e}")
            _modelo_pipeline = None

    return _modelo_pipeline


def _detectar_risco(texto: str, sentimento: str) -> str:
    """
    Classifica o nível de risco em: 'baixo', 'medio' ou 'alto'.
    """
    texto_lower = texto.lower()
    # 1. Risco alto: presença de termos explícitos de ideação suicida ou crise
    if any(termo in texto_lower for termo in PALAVRAS_RISCO_ALTO):
        return 'alto'

    # 2. Risco médio: sentimento classificado como negativo pelo modelo
    if sentimento == 'negativo':
        return 'medio'

    # 3. Risco baixo: neutro ou positivo
    return 'baixo'


def _analise_lexica_fallback(texto: str) -> str:
    """Classificador heurístico de fallback caso o arquivo .pkl esteja indisponível."""
    texto_lower = texto.lower()
    if any(p in texto_lower for p in TERMOS_RISCO_FALLBACK):
        return 'negativo'
    if any(p in texto_lower for p in TERMOS_POSITIVOS_FALLBACK):
        return 'positivo'
    return 'neutro'


def analisar_texto(texto: str) -> tuple[str, str]:
    """
    Executa a inferência real de Machine Learning no texto fornecido.
    
    Retorna uma tupla (sentimento, nivel_risco):
      - sentimento : 'positivo' | 'neutro' | 'negativo'
      - nivel_risco: 'baixo'    | 'medio'  | 'alto'
    """
    if not texto or not texto.strip():
        return 'neutro', 'baixo'

    # 1. Checagem prioritária de risco crítico
    texto_lower = texto.lower()
    tem_risco_critico = any(t in texto_lower for t in PALAVRAS_RISCO_ALTO)

    # 2. Execução da predição com o modelo de Machine Learning
    modelo = _carregar_modelo()
    sentimento = None

    if modelo is not None:
        try:
            texto_limpo = _limpar_texto(texto)
            pred = modelo.predict([texto_limpo])[0]
            pred_str = str(pred).lower().strip()

            if 'pos' in pred_str or pred_str in ['1', 'positivo']:
                sentimento = 'positivo'
            elif 'neg' in pred_str or pred_str in ['-1', 'negativo']:
                sentimento = 'negativo'
            else:
                sentimento = 'neutro'
        except Exception as e:
            print(f"[ML_UTILS] Erro na predição do modelo: {e}")
            sentimento = None

    # 3. Fallback inteligente se o modelo não estiver disponível ou falhar
    if sentimento is None:
        sentimento = _analise_lexica_fallback(texto)

    # 4. Se tiver risco crítico, sentimento negativo e risco alto imediatos
    if tem_risco_critico:
        sentimento = 'negativo'
        risco = 'alto'
    else:
        risco = _detectar_risco(texto, sentimento)

    return sentimento, risco


def analisar_texto_com_modelo(texto: str) -> tuple[str, str]:
    """Alias para retrocompatibilidade."""
    return analisar_texto(texto)