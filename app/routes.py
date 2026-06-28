import os
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError

from .models import db, Usuario, Postagem, MensagemSuriel, Reacao
from .ml_utils import analisar_texto
from . import suriel as suriel_engine

bp = Blueprint('main', __name__)
bcrypt = Bcrypt()


# ─────────────────────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/entrar', methods=['GET', 'POST'])
@bp.route('/login',  methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.feed'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and bcrypt.check_password_hash(usuario.senha_hash, senha):
            login_user(usuario, remember=True)
            return redirect(url_for('main.feed'))

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('login.html')


@bp.route('/criar-conta', methods=['GET', 'POST'])
@bp.route('/cadastro',    methods=['GET', 'POST'])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for('main.feed'))

    if request.method == 'POST':
        nome  = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        if not nome or not email or not senha:
            flash('Preencha todos os campos.', 'danger')
        elif len(senha) < 6:
            flash('A senha precisa ter pelo menos 6 caracteres.', 'danger')
        elif Usuario.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado.', 'danger')
        else:
            novo = Usuario(
                nome=nome,
                email=email,
                senha_hash=bcrypt.generate_password_hash(senha).decode('utf-8')
            )
            db.session.add(novo)
            db.session.commit()
            login_user(novo, remember=True)
            return redirect(url_for('main.feed'))

    return render_template('cadastro.html')


@bp.route('/sair')
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada.', 'success')
    return redirect(url_for('main.login'))


# ─────────────────────────────────────────────────────────────────────────────
# FEED
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/')
@login_required
def feed():
    postagens = (
        Postagem.query
        .order_by(Postagem.criado_em.desc())
        .all()
    )
    apoios_usuario = set(
        r.postagem_id for r in
        Reacao.query.filter_by(usuario_id=current_user.id, tipo='apoio').all()
    )
    return render_template('feed.html', postagens=postagens,
                           apoios_usuario=apoios_usuario)


@bp.route('/criar-post', methods=['POST'])
@login_required
def criar_post():
    texto   = request.form.get('conteudo', '').strip()
    anonimo = request.form.get('anonimo') == 'true'

    if not texto:
        flash('Escreva algo antes de publicar.', 'danger')
        return redirect(url_for('main.feed'))

    sentimento, risco = analisar_texto(texto)
    post = Postagem(
        texto=texto,
        anonimo=anonimo,
        sentimento=sentimento,
        nivel_risco=risco,
        usuario_id=current_user.id,
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('main.feed'))


@bp.route('/apagar-post/<int:post_id>', methods=['POST'])
@login_required
def apagar_post(post_id):
    post = Postagem.query.get_or_404(post_id)
    # Só o próprio autor pode apagar
    if post.usuario_id != current_user.id:
        flash('Você não tem permissão para remover esta publicação.', 'danger')
        return redirect(url_for('main.feed'))
    db.session.delete(post)
    db.session.commit()
    flash('Publicação removida.', 'success')
    return redirect(url_for('main.perfil'))


@bp.route('/apoiar/<int:post_id>', methods=['POST'])
@login_required
def apoiar(post_id):
    Postagem.query.get_or_404(post_id)
    try:
        db.session.add(Reacao(
            tipo='apoio',
            postagem_id=post_id,
            usuario_id=current_user.id
        ))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()   # já apoiou antes — ignora
    return redirect(url_for('main.feed'))


@bp.route('/feedback/<int:post_id>/<int:correto>')
@login_required
def feedback(post_id, correto):
    post = Postagem.query.get_or_404(post_id)
    if correto == 0:
        mapa = {'positivo': 'negativo', 'negativo': 'positivo', 'neutro': 'neutro'}
        post.sentimento  = mapa.get(post.sentimento, 'neutro')
        post.nivel_risco = 'medio' if post.sentimento == 'negativo' else 'baixo'
        db.session.commit()
    return redirect(url_for('main.feed'))


# ─────────────────────────────────────────────────────────────────────────────
# SURIEL
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/suriel')
@login_required
def suriel_chat():
    historico = (
        MensagemSuriel.query
        .filter_by(usuario_id=current_user.id)
        .order_by(MensagemSuriel.criado_em.asc())
        .all()
    )
    if not historico:
        msg = MensagemSuriel(
            papel='suriel',
            conteudo=suriel_engine.primeira_mensagem(),
            usuario_id=current_user.id,
        )
        db.session.add(msg)
        db.session.commit()
        historico = [msg]

    return render_template('suriel.html', historico=historico)


@bp.route('/suriel/mensagem', methods=['POST'])
@login_required
def suriel_mensagem():
    dados = request.get_json(silent=True) or {}
    texto = dados.get('mensagem', '').strip()

    if not texto:
        return jsonify({'erro': 'Mensagem vazia'}), 400

    # Salva mensagem do usuário
    db.session.add(MensagemSuriel(
        papel='user',
        conteudo=texto,
        usuario_id=current_user.id
    ))
    db.session.commit()

    # Busca histórico para contexto (exclui a mensagem recém-salva)
    historico_db = (
        MensagemSuriel.query
        .filter_by(usuario_id=current_user.id)
        .order_by(MensagemSuriel.criado_em.asc())
        .all()
    )
    historico = [{'papel': m.papel, 'conteudo': m.conteudo}
                 for m in historico_db[:-1]]

    resposta = suriel_engine.responder(texto, historico)

    # Salva resposta do Suriel
    db.session.add(MensagemSuriel(
        papel='suriel',
        conteudo=resposta,
        usuario_id=current_user.id
    ))
    db.session.commit()

    return jsonify({'resposta': resposta})


@bp.route('/suriel/limpar', methods=['POST'])
@login_required
def suriel_limpar():
    MensagemSuriel.query.filter_by(usuario_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for('main.suriel_chat'))


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/dashboard')
@login_required
def dashboard():
    dias  = int(request.args.get('periodo', 7))
    corte = datetime.utcnow() - timedelta(days=dias)

    # Filtra trazendo apenas posts criados dentro do limite selecionado (1, 7 ou 30 dias)
    posts = (
        Postagem.query
        .filter(
            Postagem.usuario_id == current_user.id,
            Postagem.criado_em >= corte
        )
        .all()
    )

    total = len(posts)
    cont  = {'positivo': 0, 'neutro': 0, 'negativo': 0}
    
    for p in posts:
        sent_limpo = p.sentimento.lower().strip()
        if 'positivo' in sent_limpo:
            cont['positivo'] += 1
        elif 'risco' in sent_limpo or 'negativo' in sent_limpo:
            cont['negativo'] += 1
        else:
            cont['neutro'] += 1

    if total > 0:
        paz      = round(cont['positivo']  / total * 100)
        neutro   = round(cont['neutro']    / total * 100)
        negativo = round(cont['negativo']  / total * 100)
    else:
        paz = neutro = negativo = 0

    if negativo >= 40:
        estado = 'Atenção'
    elif paz >= 50:
        estado = 'Sereno'
    else:
        estado = 'Equilibrado'

    return render_template(
        'dashboard.html',
        metrica_data={
            'paz': paz, 'neutro': neutro,
            'negativo': negativo, 'estado': estado
        },
        periodo_selecionado=dias
    )

# ─────────────────────────────────────────────────────────────────────────────
# PERFIL
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/perfil')
@login_required
def perfil():
    minhas_postagens = (
        Postagem.query
        .filter_by(usuario_id=current_user.id)
        .order_by(Postagem.criado_em.desc())
        .limit(20)
        .all()
    )
    return render_template('perfil.html', minhas_postagens=minhas_postagens)


@bp.route('/perfil/excluir', methods=['POST'])
@login_required
def excluir_conta():
    usuario = current_user._get_current_object()
    logout_user()
    db.session.delete(usuario)   # cascade apaga postagens, mensagens e reações
    db.session.commit()
    flash('Conta e todos os dados removidos permanentemente.', 'success')
    return redirect(url_for('main.login'))

