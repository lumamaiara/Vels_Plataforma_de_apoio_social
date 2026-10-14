"""
suriel.py — Motor do Chatbot Suriel (Arquitetura Híbrida e Resiliente)
Plataforma Vels — TCC Luma Maiara / UFPI

Hierarquia de Atendimento:
1. Protocolo Crítico de Segurança (CVV 188): acionamento imediato em caso de risco de vida.
2. Integração com IA Generativa (Google Gemini ou Anthropic Claude com System Prompt clínico/empático).
3. Fallback Empático Contextual: garante 100% de disponibilidade mesmo sem internet ou sem créditos de API.
"""
import os
import random
import re
from dotenv import load_dotenv

load_dotenv()

# ── Termos de Crise Imediata (Salvaguarda Incondicional) ────────────────────────
PALAVRAS_CRISE = [
    'suicídio', 'suicidio', 'suicidar', 'me matar', 'quero morrer',
    'não quero mais viver', 'nao quero mais viver', 'acabar com tudo',
    'me machucar', 'me ferir', 'autolesão', 'autolesao', 'me cortar',
    'não vejo saída', 'nao vejo saida', 'desaparecer para sempre',
    'ninguém sentirá minha falta', 'ninguem sentira minha falta',
    'pensei em me matar', 'tentativa de suicídio', 'quero acabar',
    'não quero mais existir', 'nao quero mais existir', 'tirar minha vida',
    'dar um fim na minha vida'
]

RESPOSTA_CRISE = (
    "Obrigado por compartilhar isso comigo. Quero que saiba que o que você está "
    "sentindo é real e legítimo, mas você **não precisa enfrentar essa dor sozinho(a)**.\n\n"
    "Por favor, entre em contato agora mesmo com o **CVV — Centro de Valorização da Vida**:\n"
    "• Ligue **188** (ligação gratuita, 24 horas por dia, totalmente confidencial)\n"
    "• Acesse o chat online em **[cvv.org.br](https://www.cvv.org.br)**\n\n"
    "No CVV você encontrará pessoas preparadas para te acolher com respeito e sem nenhum julgamento. "
    "Estou aqui com você, mas recomendo fortemente que busque esse apoio imediato agora. Você consegue fazer essa ligação?"
)

SYSTEM_PROMPT = (
    "Você é o Suriel, o assistente de acolhimento e escuta emocional da plataforma Vels.\n"
    "A Vels é um espaço seguro digital para pessoas que enfrentam sofrimento psicológico, depressão ou ansiedade.\n\n"
    "DIRETRIZES FUNDAMENTAIS:\n"
    "1. Seu propósito é oferecer escuta ativa, calorosa, empática e acolhedora.\n"
    "2. Você NUNCA é psicólogo nem médico e NUNCA prescreve remédios ou diagnósticos.\n"
    "3. Valide os sentimentos do usuário antes de qualquer intervenção (evite positividade tóxica como 'vai passar' ou 'seja forte').\n"
    "4. Mantenha respostas concisas (2 a 4 parágrafos curtos), calorosas e naturais em Português do Brasil.\n"
    "5. Sempre termine com uma pergunta gentil e aberta para encorajar a continuidade do diálogo.\n"
    "6. Em caso de sofrimento agudo, incentive a busca por psicoterapia ou redes de apoio locais."
)

# ── Banco de Respostas de Fallback Humanizado ──────────────────────────────────
RESPOSTAS_CONTEXTUAIS = [
    (
        "Sinto muito que você esteja carregando esse peso. Às vezes o cansaço mental "
        "acumulado faz com que cada pequena tarefa pareça uma montanha difícil de subir.\n\n"
        "Quero que saiba que este é um espaço seguro para você desabafar no seu próprio ritmo. "
        "O que você sente que mais contribuiu para essa sobrecarga hoje?"
    ),
    (
        "Obrigado por ter coragem de colocar isso em palavras. Quando estamos machucados por dentro, "
        "o silêncio muitas vezes parece a única opção, mas dividir o que se sente já é um passo muito valioso.\n\n"
        "Respeite o seu momento e suas pausas. Se pudesse fazer apenas uma coisa gentil por si mesmo(a) agora, o que seria?"
    ),
    (
        "Eu ouço você com atenção e acolhimento. É completamente compreensível sentir-se assim quando as coisas "
        "fogem do nosso controle ou quando nos cobramos além da conta.\n\n"
        "Lembre-se de que você não precisa resolver tudo de uma vez. Como posso te apoiar da melhor forma neste instante?"
    ),
    (
        "Compreendo a densidade do que você compartilhou. Sentimentos difíceis demandam tempo e cuidado, "
        "e não há pressa para encontrar todas as respostas agora.\n\n"
        "Você gostaria de contar um pouco mais sobre como tem sido a sua rotina nos últimos dias?"
    ),
]


def detectar_crise(texto: str) -> bool:
    """Verifica se há menção explícita a termos de crise ou ideação suicida."""
    texto_lower = texto.lower()
    return any(p in texto_lower for p in PALAVRAS_CRISE)


def primeira_mensagem() -> str:
    """Mensagem de boas-vindas na abertura do chat."""
    return (
        "Olá. Sou o Suriel, seu espaço seguro de acolhimento e reflexão emocional na plataforma Vels.\n\n"
        "Tudo o que você compartilha aqui é totalmente confidencial e livre de julgamentos. "
        "Como você está se sentindo hoje?"
    )


def _responder_com_gemini(mensagem_usuario: str, historico: list[dict], api_key: str) -> str:
    """Tenta gerar resposta empática via Google GenAI API (Gemini 3.8 Flash)."""
    from google import genai
    client = genai.Client(api_key=api_key)

    contexto = ""
    for h in (historico or [])[-4:]:
        autor = "Usuário" if h.get('papel') == 'user' else "Suriel"
        contexto += f"{autor}: {h.get('conteudo', '')}\n"

    prompt_completo = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Histórico recente:\n{contexto}\n"
        f"Usuário: {mensagem_usuario}\n"
        f"Suriel (resposta acolhedora e empática):"
    )

    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=prompt_completo,
    )
    return response.text.strip()


def _responder_com_claude(mensagem_usuario: str, historico: list[dict], api_key: str) -> str:
    """Tenta gerar resposta empática via Anthropic Claude API."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    mensagens = []
    for h in historico[-6:]:
        role = 'user' if h.get('papel') == 'user' else 'assistant'
        mensagens.append({'role': role, 'content': h.get('conteudo', '')})
    mensagens.append({'role': 'user', 'content': mensagem_usuario})

    # Garante início com user
    if mensagens and mensagens[0]['role'] == 'assistant':
        mensagens = mensagens[1:]

    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=mensagens,
    )
    return response.content[0].text.strip()


def responder(mensagem_usuario: str, historico: list[dict] | None = None) -> str:
    """
    Processa a resposta do Suriel combinando:
    1. Salvaguarda prioritária de crise (CVV).
    2. LLM via Gemini ou Claude.
    3. Fallback empático contextual 100% resiliente.
    """
    historico = historico or []

    # 1. Checagem Incondicional de Segurança e Vida (CVV 188)
    if detectar_crise(mensagem_usuario):
        return RESPOSTA_CRISE

    # 2. Tentativa com Anthropic Claude
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if anthropic_key and anthropic_key.startswith('sk-ant-') and 'SUA_CHAVE' not in anthropic_key:
        try:
            return _responder_com_claude(mensagem_usuario, historico, anthropic_key)
        except Exception as e:
            print(f"[SURIEL] Falha na API Claude: {e}")

    # 3. Tentativa com Google Gemini
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key and len(gemini_key) > 20:
        try:
            return _responder_com_gemini(mensagem_usuario, historico, gemini_key)
        except Exception as e:
            print(f"[SURIEL] Falha na API Gemini: {e}")

    # 4. Fallback Empático Resiliente (Garante que nunca há erro 500 ou mensagem de falha)
    return random.choice(RESPOSTAS_CONTEXTUAIS)