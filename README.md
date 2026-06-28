# Vels — Backend Completo

## Como rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. (Opcional) Treinar o modelo de ML
python scripts/train_model_real.py

# 3. Configurar a chave da API (para o Suriel)
export GEMINI_API_KEY="AQ.Ab-..."

# 4. Rodar o servidor
python run.py
```

Acesse: http://localhost:5000

## Estrutura

```
vels_backend/
├── app/
│   ├── __init__.py       ← Factory da aplicação
│   ├── models.py         ← Banco de dados (Usuario, Postagem, MensagemSuriel, Reacao)
│   ├── routes.py         ← Todas as rotas (auth, feed, suriel, dashboard, perfil)
│   ├── suriel.py         ← Motor do chatbot Suriel (API Anthropic)
│   ├── ml_utils.py       ← Integração com modelo de ML
│   ├── models_ml/        ← modelo_sentimento.pkl (gerado pelo treino)
│   ├── templates/        ← HTML (base, entrar, feed, suriel, dashboard, perfil)
│   └── static/css/       ← vels.css
├── scripts/
│   ├── data_cleaning.py  ← Pré-processamento PLN
│   └── train_model_real.py ← Treino com dataset real
├── run.py
└── requirements.txt
```
