"""
models.py — Modelos de banco de dados da Plataforma Vels
Inclui: Usuario, Postagem, MensagemSuriel, Reacao
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class Usuario(UserMixin, db.Model):
    """Usuário da plataforma."""
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash    = db.Column(db.String(200), nullable=False)
    anonimo       = db.Column(db.Boolean, default=False)   # preferência padrão
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)

    postagens     = db.relationship('Postagem', backref='autor', lazy=True,
                                    cascade='all, delete-orphan')
    mensagens     = db.relationship('MensagemSuriel', backref='usuario',
                                    lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Usuario {self.email}>'


class Postagem(db.Model):
    """Post no feed da comunidade."""
    id            = db.Column(db.Integer, primary_key=True)
    texto         = db.Column(db.Text, nullable=False)
    anonimo       = db.Column(db.Boolean, default=False)
    sentimento    = db.Column(db.String(20), default='neutro')   # positivo/neutro/negativo
    nivel_risco   = db.Column(db.String(10), default='baixo')    # baixo/medio/alto
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)

    reacoes       = db.relationship('Reacao', backref='postagem', lazy=True,
                                    cascade='all, delete-orphan')

    def total_apoios(self):
        return Reacao.query.filter_by(postagem_id=self.id, tipo='apoio').count()

    def nome_exibicao(self):
        if self.anonimo or not self.autor:
            return 'Anônimo'
        return self.autor.nome

    def badge_sentimento(self):
        mapa = {
            'positivo': ('Sentimento Positivo', 'badge-positivo'),
            'neutro':   ('Neutro',               'badge-neutro'),
            'negativo': ('Sinal de Risco',        'badge-risco'),
        }
        return mapa.get(self.sentimento, ('Neutro', 'badge-neutro'))


class MensagemSuriel(db.Model):
    """Histórico de conversa com o chatbot Suriel."""
    id            = db.Column(db.Integer, primary_key=True)
    papel         = db.Column(db.String(10), nullable=False)  # 'user' ou 'suriel'
    conteudo      = db.Column(db.Text, nullable=False)
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Reacao(db.Model):
    """Apoio ou comentário em uma postagem."""
    id            = db.Column(db.Integer, primary_key=True)
    tipo          = db.Column(db.String(20), nullable=False)   # 'apoio'
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)
    postagem_id   = db.Column(db.Integer, db.ForeignKey('postagem.id'), nullable=False)
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
