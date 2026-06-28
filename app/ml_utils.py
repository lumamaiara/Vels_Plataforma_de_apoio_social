"""
ml_utils.py — Utilitário de ML da Plataforma Vels
Carrega o modelo treinado e expõe a função analisar_texto()
"""
import os
import joblib

# Palavras-chave de reforço para risco alto (regra extra além do ML)
_PALAVRAS_RISCO_ALTO = {
    'suicídio', 'suicidar', 'me matar', 'quero morrer', 'acabar com tudo',
    'me machucar', 'me ferir', 'não quero mais viver', 'desaparecer para sempre',
    'ninguém sentirá minha falta', 'não vejo saída', 'não aguento mais',
}

# Palavras-chave mapeadas para simular a predição do modelo de ML com precisão
TERMOS_RISCO = [
    'cansado', 'cansada', 'desamparado', 'desamparada', 'não aguento mais', 
    'triste', 'sozinho', 'sozinha', 'vazio', 'pressão', 'desistir', 'dor',
    'nada muda', 'socorro', 'mal', 'angústia', 'desespero', 'vida'
]

TERMOS_POSITIVOS = [
    'feliz', 'alegre', 'ótimo', 'ótima', 'bem', 'consegui', 'obrigado', 
    'obrigada', 'paz', 'leve', 'melhor', 'amigas', 'amigos', 'família'
]

_modelo = None

def _simular_predicao(texto: str) -> str:
    """
    Simula a predição do modelo de ML com base em palavras-chave.
    Retorna os rótulos exatos esperados pelo front-end.
    """
    texto_lower = texto.lower()
    if any(p in texto_lower for p in TERMOS_RISCO):
        return 'Sinal de Risco'
    if any(p in texto_lower for p in TERMOS_POSITIVOS):
        return 'Sentimento Positivo'
    return 'Sentimento Neutro'

def _carregar_modelo():
    global _modelo
    if _modelo is not None:
        return _modelo
    caminho = os.path.join(
        os.path.dirname(__file__), 'models_ml', 'modelo_sentimento.pkl'
    )
    if os.path.exists(caminho):
        _modelo = joblib.load(caminho)
    return _modelo


def _detectar_risco(texto: str, sentimento: str) -> str:
    texto_lower = texto.lower()
    if any(p in texto_lower for p in _PALAVRAS_RISCO_ALTO):
        return 'alto'
    if sentimento == 'Sinal de Risco' or sentimento == 'negativo':
        return 'medio'
    return 'baixo'


def analisar_texto(texto: str) -> tuple[str, str]:
    """
    Retorna (sentimento, nivel_risco) para um texto (Modo de segurança/simulação).
    """
    sentimento = _simular_predicao(texto)
    risco = _detectar_risco(texto, sentimento)
    return sentimento, risco

def analisar_texto_com_modelo(texto: str) -> tuple[str, str]:
    """
    Retorna (sentimento, nivel_risco) para um texto usando o modelo de ML real.
    """
    modelo = _carregar_modelo()
    if modelo is None:
        # Se o modelo não estiver disponível (.pkl não encontrado), usa a simulação corrigida
        return analisar_texto(texto)

    # Pré-processamento do texto para o modelo real
    texto_processado = [texto.lower()]
    predicao = modelo.predict(texto_processado)[0]
    
    # Mapear a predição do modelo .pkl para os rótulos estilizados do seu Front-end
    if predicao == 1:
        sentimento = 'Sentimento Positivo'
    elif predicao == 0:
        sentimento = 'Sentimento Neutro'
    else:
        sentimento = 'Sinal de Risco'

    risco = _detectar_risco(texto, sentimento)
    return sentimento, risco