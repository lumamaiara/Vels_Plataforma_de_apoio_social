"""
data_cleaning.py — Pré-processamento de texto em Português
Plataforma Vels — TCC Luma Maiara / UFPI

Correção principal: stopwords padrão removem 'não', 'nunca', 'jamais'
que são palavras-chave para detectar sentimentos negativos.
"""

import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)

# Palavras que NÃO devem ser removidas pois carregam carga emocional
PALAVRAS_MANTER = {
    'não', 'nao', 'nunca', 'jamais', 'nenhum', 'nenhuma',
    'nem', 'sem', 'mal', 'nada', 'mais', 'muito', 'demais',
    'sozinha', 'sozinho', 'dor', 'medo', 'triste', 'tristeza',
    'vazia', 'vazio', 'pior', 'péssima', 'péssimo',
    'desesperada', 'desesperado', 'limite', 'fim', 'fardo'
}

STOPWORDS_PT = set(stopwords.words('portuguese')) - PALAVRAS_MANTER


def limpar_texto(texto: str) -> str:
    """
    Pipeline completo de pré-processamento PLN:
    1. Minúsculas
    2. Remove URLs e menções
    3. Remove pontuação (mantém reticências como marcador)
    4. Tokenização
    5. Remoção de stopwords (com preservação de negações)
    """
    if not texto or not isinstance(texto, str):
        return ""

    # 1. Minúsculas
    texto = texto.lower()

    # 2. Remove URLs e menções
    texto = re.sub(r'http\S+|www\S+|@\w+|#\w+', '', texto)

    # 3. Substitui reticências por marcador e remove demais pontuações
    texto = re.sub(r'\.{2,}', ' reticencias ', texto)
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\d+', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()

    # 4. Tokenização
    try:
        tokens = word_tokenize(texto, language='portuguese')
    except Exception:
        tokens = texto.split()

    # 5. Remove stopwords (preservando negações emocionais)
    tokens_limpos = [t for t in tokens if t not in STOPWORDS_PT and len(t) > 1]

    return " ".join(tokens_limpos)


if __name__ == "__main__":
    testes = [
        "Não aguento mais essa dor, estou no meu limite",
        "Hoje me senti muito melhor, consegui sair de casa!",
        "Fui à consulta hoje. Foi uma conversa tranquila.",
    ]
    for t in testes:
        print(f"Original : {t}")
        print(f"Limpo    : {limpar_texto(t)}\n")
