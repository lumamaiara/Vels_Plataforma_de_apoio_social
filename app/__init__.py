"""
app/__init__.py — Application Factory da Plataforma Vels
"""
from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from datetime import datetime

from .models import db, Usuario

login_manager = LoginManager()
bcrypt = Bcrypt()


def create_app(config: dict | None = None):
    app = Flask(__name__)

    # ── Configurações ──────────────────────────────────────────────────────
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vels.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'vels-tcc-luma-ufpi-2025-chave-secreta'

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

    return app
