"""
run.py — Ponto de entrada da Plataforma Vels
Execute: python run.py
"""
import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # O Suriel agora utiliza a API do Gemini configurada via .env
    print("\n🚀 Plataforma Vels iniciada. Suriel online.")
    app.run(debug=True, host='0.0.0.0', port=5000)