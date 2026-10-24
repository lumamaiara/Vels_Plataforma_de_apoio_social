"""
app/__init__.py — Application Factory da Plataforma Vels 
"""
import os
from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from .models import db, Usuario

login_manager = LoginManager()
bcrypt = Bcrypt()


def create_app(config: dict | None = None):
    app = Flask(__name__)

    # ── Configurações de Banco e Segurança ─────────────────────────────────
    secret_key = os.environ.get('SECRET_KEY', 'vels-tcc-luma-ufpi-2025-chave-secreta')
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        # Corrige URI legada do PostgreSQL para SQLAlchemy 2.0
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
    else:
        # Fallback local para desenvolvimento: SQLite na pasta instance
        if os.environ.get('VERCEL') == '1':
            db_path = '/tmp/vels.db'
        else:
            db_path = os.path.join(app.instance_path, 'vels.db')
            os.makedirs(app.instance_path, exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = secret_key

    # ── Blindagem de Cookies de Sessão (Anti-XSS e Anti-CSRF) ──────────────
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Habilita cookie Secure se em ambiente de produção ou Vercel (HTTPS)
    app.config['SESSION_COOKIE_SECURE'] = (
        os.environ.get('FLASK_ENV') == 'production' or os.environ.get('VERCEL') == '1'
    )
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    if config:
        app.config.update(config)

    # ── Extensões ──────────────────────────────────────────────────────────
    db.init_app(app)
    bcrypt.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Faça login para acessar esta página.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def carregar_usuario(user_id):
        return Usuario.query.get(int(user_id))

    # ── Registro do Blueprint ──────────────────────────────────────────────
    from .routes import bp, bcrypt as bp_bcrypt
    bp_bcrypt.init_app(app)
    app.register_blueprint(bp)

    # ── Banco de dados ─────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    # ── Cabeçalhos de Segurança HTTP Defensivos ─────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    return app