import os
import uuid
from datetime import datetime
from functools import wraps

from flask import render_template, request, redirect, url_for, abort, flash, session, jsonify
from flask_login import current_user, login_user, login_required, logout_user
from werkzeug.utils import secure_filename

from app import app, db, login_manager
from app.forms import (
    CadastroForm, LoginForm, PizzaForm, IngredienteForm, CategoriaForm,
    ConfiguracaoForm, StatusPedidoForm, CheckoutForm, MontarPizzaForm
)
from app.models import (
    Usuario, PerfilEnum, CategoriaPizza, Pizza, Ingrediente, TipoIngredienteEnum,
    Pedido, ItemPedido, ItemPedidoIngrediente, StatusPedidoEnum, Configuracao
)


# ── Utilitários ──────────────────────────────────────────────────────────────

def perfil_requerido(*perfis):
    def decorador(funcao):
        @wraps(funcao)
        def rota_protegida(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.perfil not in perfis:
                abort(403)
            return funcao(*args, **kwargs)
        return rota_protegida
    return decorador


def salvar_imagem(arquivo, pasta_destino):
    if not arquivo or not arquivo.filename:
        return None
    extensao = secure_filename(arquivo.filename).rsplit('.', 1)[-1].lower()
    nome_arquivo = f'{uuid.uuid4().hex}.{extensao}'
    arquivo.save(os.path.join(pasta_destino, nome_arquivo))
    return nome_arquivo


def remover_imagem(pasta_destino, nome_arquivo):
    if not nome_arquivo:
        return
    caminho = os.path.join(pasta_destino, nome_arquivo)
    if os.path.isfile(caminho):
        try:
            os.remove(caminho)
        except OSError:
            pass


def obter_carrinho():
    return session.setdefault('carrinho', [])


def salvar_carrinho(carrinho):
    session['carrinho'] = carrinho
    session.modified = True


def calcular_total_carrinho(carrinho):
    return sum(item['subtotal'] for item in carrinho)


@app.context_processor
def injetar_globais():
    carrinho = session.get('carrinho', [])
    return {
        'carrinho_quantidade': sum(item['quantidade'] for item in carrinho),
        'carrinho_total': calcular_total_carrinho(carrinho),
        'config_loja': Configuracao.query.first(),
        'PerfilEnum': PerfilEnum
    }


# ── Páginas públicas ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    destaques = Pizza.query.filter_by(ativo=True).order_by(Pizza.id.desc()).limit(6).all()
    return render_template('index.html', destaques=destaques)


@app.route('/cardapio')
def cardapio():
    categoria_id = request.args.get('categoria', type=int)
    categorias = CategoriaPizza.query.order_by(CategoriaPizza.nome).all()

    consulta = Pizza.query.filter_by(ativo=True)
    if categoria_id:
        consulta = consulta.filter_by(categoria_id=categoria_id)
    pizzas = consulta.order_by(Pizza.nome).all()

    return render_template('cardapio.html', pizzas=pizzas, categorias=categorias, categoria_id=categoria_id)


@app.route('/localizacao')
def localizacao():
    config = Configuracao.query.first()
    return render_template('localizacao.html', config=config)


@app.route('/monte-sua-pizza')
def monte_pizza():
    config = Configuracao.query.first()
    ingredientes = Ingrediente.query.filter_by(ativo=True).order_by(Ingrediente.tipo, Ingrediente.nome).all()

    grupos = {}
    for ingrediente in ingredientes:
        grupos.setdefault(ingrediente.tipo, []).append(ingrediente)

    form = MontarPizzaForm()
    return render_template('monte_pizza.html', grupos=grupos, config=config, form=form)


# ── Autenticação ─────────────────────────────────────────────────────────────

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = CadastroForm()
    if form.validate_on_submit():
        if Usuario.query.filter_by(email=form.email.data.lower().strip()).first():
            flash('Já existe uma conta com esse e-mail.', 'danger')
            return render_template('cadastro.html', form=form)

        usuario = Usuario(
            nome=form.nome.data.strip(),
            email=form.email.data.lower().strip(),
            telefone=form.telefone.data,
            endereco=form.endereco.data,
            perfil=PerfilEnum.CLIENTE
        )
        usuario.set_senha(form.senha.data)
        db.session.add(usuario)
        db.session.commit()

        login_user(usuario)
        flash(f'Conta criada com sucesso! Bem-vindo(a), {usuario.nome}.', 'success')
        return redirect(url_for('index'))

    return render_template('cadastro.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data.lower().strip()).first()
        if usuario and usuario.checar_senha(form.senha.data):
            login_user(usuario)
            flash(f'Bem-vindo(a) de volta, {usuario.nome}!', 'success')
            proxima = request.args.get('next')
            return redirect(proxima or url_for('index'))
        flash('E-mail ou senha inválidos.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('index'))


# ── Carrinho ─────────────────────────────────────────────────────────────────

@app.route('/carrinho')
def carrinho():
    itens = obter_carrinho()
    total = calcular_total_carrinho(itens)
    return render_template('carrinho.html', itens=itens, total=total)


@app.route('/carrinho/adicionar/<int:pizza_id>', methods=['POST'])
def carrinho_adicionar_pizza(pizza_id):
    pizza = Pizza.query.filter_by(id=pizza_id, ativo=True).first_or_404()
    try:
        quantidade = max(1, int(request.form.get('quantidade', 1)))
    except (TypeError, ValueError):
        quantidade = 1

    carrinho_atual = obter_carrinho()
    carrinho_atual.append({
        'tipo': 'cardapio',
        'pizza_id': pizza.id,
        'nome': pizza.nome,
        'preco_unitario': float(pizza.preco),
        'quantidade': quantidade,
        'subtotal': float(pizza.preco) * quantidade,
        'ingredientes': []
    })
    salvar_carrinho(carrinho_atual)

    flash(f'"{pizza.nome}" foi adicionada ao carrinho!', 'success')
    return redirect(request.referrer or url_for('cardapio'))


@app.route('/carrinho/adicionar-montada', methods=['POST'])
def carrinho_adicionar_montada():
    config = Configuracao.query.first()
    preco_base = float(config.preco_base_montagem) if config else 0

    ids_selecionados = request.form.getlist('ingredientes')
    try:
        quantidade = max(1, int(request.form.get('quantidade', 1)))
    except (TypeError, ValueError):
        quantidade = 1

    ingredientes_validos = []
    if ids_selecionados:
        ingredientes_validos = Ingrediente.query.filter(
            Ingrediente.id.in_(ids_selecionados),
            Ingrediente.ativo.is_(True)
        ).all()

    preco_unitario = preco_base + sum(float(i.preco) for i in ingredientes_validos)

    carrinho_atual = obter_carrinho()
    carrinho_atual.append({
        'tipo': 'montada',
        'pizza_id': None,
        'nome': 'Pizza Montada por Você',
        'preco_unitario': preco_unitario,
        'quantidade': quantidade,
        'subtotal': preco_unitario * quantidade,
        'ingredientes': [{'nome': i.nome, 'preco': float(i.preco)} for i in ingredientes_validos]
    })
    salvar_carrinho(carrinho_atual)

    flash('Sua pizza personalizada foi adicionada ao carrinho!', 'success')
    return redirect(url_for('carrinho'))


@app.route('/carrinho/remover/<int:indice>', methods=['POST'])
def carrinho_remover(indice):
    carrinho_atual = obter_carrinho()
    if 0 <= indice < len(carrinho_atual):
        carrinho_atual.pop(indice)
        salvar_carrinho(carrinho_atual)
        flash('Item removido do carrinho.', 'info')
    return redirect(url_for('carrinho'))


@app.route('/carrinho/limpar', methods=['POST'])
def carrinho_limpar():
    salvar_carrinho([])
    flash('Carrinho esvaziado.', 'info')
    return redirect(url_for('carrinho'))


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    itens = obter_carrinho()
    if not itens:
        flash('Seu carrinho está vazio.', 'warning')
        return redirect(url_for('cardapio'))

    form = CheckoutForm()
    if request.method == 'GET':
        form.endereco_entrega.data = current_user.endereco

    if form.validate_on_submit():
        total = calcular_total_carrinho(itens)

        pedido = Pedido(
            usuario_id=current_user.id,
            status=StatusPedidoEnum.PENDENTE,
            endereco_entrega=form.endereco_entrega.data,
            forma_pagamento=form.forma_pagamento.data,
            observacoes=form.observacoes.data,
            total=total
        )
        db.session.add(pedido)
        db.session.flush()  # garante pedido.id antes de criar os itens

        for item in itens:
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                pizza_id=item.get('pizza_id'),
                nome=item['nome'],
                tipo=item['tipo'],
                preco_unitario=item['preco_unitario'],
                quantidade=item['quantidade'],
                subtotal=item['subtotal']
            )
            db.session.add(item_pedido)
            db.session.flush()

            for ingrediente in item.get('ingredientes', []):
                db.session.add(ItemPedidoIngrediente(
                    item_pedido_id=item_pedido.id,
                    nome=ingrediente['nome'],
                    preco=ingrediente['preco']
                ))

        db.session.commit()
        salvar_carrinho([])

        flash(f'Pedido #{pedido.id} realizado com sucesso! Acompanhe o status em "Meus Pedidos".', 'success')
        return redirect(url_for('pedido_detalhe', pedido_id=pedido.id))

    total = calcular_total_carrinho(itens)
    return render_template('checkout.html', form=form, itens=itens, total=total)


# ── Área do cliente ──────────────────────────────────────────────────────────

@app.route('/meus-pedidos')
@login_required
def meus_pedidos():
    pedidos = Pedido.query.filter_by(usuario_id=current_user.id).order_by(Pedido.criado_em.desc()).all()
    return render_template('meus_pedidos.html', pedidos=pedidos)


@app.route('/meus-pedidos/<int:pedido_id>')
@login_required
def pedido_detalhe(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.usuario_id != current_user.id and current_user.perfil != PerfilEnum.ADMIN:
        abort(403)
    return render_template('pedido_detalhe.html', pedido=pedido)


# ── Administração ────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_dashboard():
    total_pizzas = Pizza.query.count()
    total_ingredientes = Ingrediente.query.count()
    total_usuarios = Usuario.query.filter_by(perfil=PerfilEnum.CLIENTE).count()
    pedidos_pendentes = Pedido.query.filter_by(status=StatusPedidoEnum.PENDENTE).count()
    ultimos_pedidos = Pedido.query.order_by(Pedido.criado_em.desc()).limit(8).all()

    return render_template(
        'admin/dashboard.html',
        total_pizzas=total_pizzas,
        total_ingredientes=total_ingredientes,
        total_usuarios=total_usuarios,
        pedidos_pendentes=pedidos_pendentes,
        ultimos_pedidos=ultimos_pedidos
    )


# — Cardápio (CRUD) —

@app.route('/admin/cardapio')
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_cardapio():
    pizzas = Pizza.query.order_by(Pizza.nome).all()
    return render_template('admin/cardapio_lista.html', pizzas=pizzas)


@app.route('/admin/cardapio/novo', methods=['GET', 'POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_cardapio_novo():
    form = PizzaForm()
    form.categoria_id.choices = [(c.id, c.nome) for c in CategoriaPizza.query.order_by(CategoriaPizza.nome).all()]

    if form.validate_on_submit():
        nome_imagem = salvar_imagem(form.imagem.data, app.config['PASTA_UPLOAD_PIZZAS'])
        pizza = Pizza(
            nome=form.nome.data.strip(),
            descricao=form.descricao.data,
            preco=form.preco.data,
            categoria_id=form.categoria_id.data,
            imagem=nome_imagem,
            ativo=form.ativo.data
        )
        db.session.add(pizza)
        db.session.commit()
        flash(f'Pizza "{pizza.nome}" cadastrada no cardápio!', 'success')
        return redirect(url_for('admin_cardapio'))

    return render_template('admin/cardapio_form.html', form=form, pizza=None)


@app.route('/admin/cardapio/editar/<int:pizza_id>', methods=['GET', 'POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_cardapio_editar(pizza_id):
    pizza = Pizza.query.get_or_404(pizza_id)
    form = PizzaForm(obj=pizza)
    form.categoria_id.choices = [(c.id, c.nome) for c in CategoriaPizza.query.order_by(CategoriaPizza.nome).all()]

    if request.method == 'GET':
        form.categoria_id.data = pizza.categoria_id

    if form.validate_on_submit():
        pizza.nome = form.nome.data.strip()
        pizza.descricao = form.descricao.data
        pizza.preco = form.preco.data
        pizza.categoria_id = form.categoria_id.data
        pizza.ativo = form.ativo.data

        if form.imagem.data and form.imagem.data.filename:
            remover_imagem(app.config['PASTA_UPLOAD_PIZZAS'], pizza.imagem)
            pizza.imagem = salvar_imagem(form.imagem.data, app.config['PASTA_UPLOAD_PIZZAS'])

        db.session.commit()
        flash(f'Pizza "{pizza.nome}" atualizada!', 'success')
        return redirect(url_for('admin_cardapio'))

    return render_template('admin/cardapio_form.html', form=form, pizza=pizza)


@app.route('/admin/cardapio/excluir/<int:pizza_id>', methods=['POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_cardapio_excluir(pizza_id):
    pizza = Pizza.query.get_or_404(pizza_id)
    remover_imagem(app.config['PASTA_UPLOAD_PIZZAS'], pizza.imagem)
    nome = pizza.nome
    db.session.delete(pizza)
    db.session.commit()
    flash(f'Pizza "{nome}" removida do cardápio.', 'info')
    return redirect(url_for('admin_cardapio'))


# — Categorias —

@app.route('/admin/categorias', methods=['GET', 'POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_categorias():
    form = CategoriaForm()
    if form.validate_on_submit():
        nome = form.nome.data.strip()
        if CategoriaPizza.query.filter(db.func.lower(CategoriaPizza.nome) == nome.lower()).first():
            flash('Essa categoria já existe.', 'warning')
        else:
            db.session.add(CategoriaPizza(nome=nome))
            db.session.commit()
            flash(f'Categoria "{nome}" criada!', 'success')
        return redirect(url_for('admin_categorias'))

    categorias = CategoriaPizza.query.order_by(CategoriaPizza.nome).all()
    return render_template('admin/categorias.html', form=form, categorias=categorias)


@app.route('/admin/categorias/excluir/<int:categoria_id>', methods=['POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_categorias_excluir(categoria_id):
    categoria = CategoriaPizza.query.get_or_404(categoria_id)
    if categoria.pizzas:
        flash('Não é possível excluir: existem pizzas nessa categoria.', 'danger')
    else:
        db.session.delete(categoria)
        db.session.commit()
        flash('Categoria removida.', 'info')
    return redirect(url_for('admin_categorias'))


# — Ingredientes (para "Monte sua Pizza") —

@app.route('/admin/ingredientes')
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_ingredientes():
    ingredientes = Ingrediente.query.order_by(Ingrediente.tipo, Ingrediente.nome).all()
    return render_template('admin/ingredientes_lista.html', ingredientes=ingredientes)


@app.route('/admin/ingredientes/novo', methods=['GET', 'POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_ingredientes_novo():
    form = IngredienteForm()
    form.tipo.choices = [(t.name, t.value) for t in TipoIngredienteEnum]

    if form.validate_on_submit():
        nome_imagem = salvar_imagem(form.imagem.data, app.config['PASTA_UPLOAD_INGREDIENTES'])
        ingrediente = Ingrediente(
            nome=form.nome.data.strip(),
            tipo=TipoIngredienteEnum[form.tipo.data],
            preco=form.preco.data,
            imagem=nome_imagem,
            ativo=form.ativo.data
        )
        db.session.add(ingrediente)
        db.session.commit()
        flash(f'Ingrediente "{ingrediente.nome}" adicionado!', 'success')
        return redirect(url_for('admin_ingredientes'))

    return render_template('admin/ingredientes_form.html', form=form, ingrediente=None)


@app.route('/admin/ingredientes/editar/<int:ingrediente_id>', methods=['GET', 'POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_ingredientes_editar(ingrediente_id):
    ingrediente = Ingrediente.query.get_or_404(ingrediente_id)
    form = IngredienteForm(obj=ingrediente)
    form.tipo.choices = [(t.name, t.value) for t in TipoIngredienteEnum]

    if request.method == 'GET':
        form.tipo.data = ingrediente.tipo.name

    if form.validate_on_submit():
        ingrediente.nome = form.nome.data.strip()
        ingrediente.tipo = TipoIngredienteEnum[form.tipo.data]
        ingrediente.preco = form.preco.data
        ingrediente.ativo = form.ativo.data

        if form.imagem.data and form.imagem.data.filename:
            remover_imagem(app.config['PASTA_UPLOAD_INGREDIENTES'], ingrediente.imagem)
            ingrediente.imagem = salvar_imagem(form.imagem.data, app.config['PASTA_UPLOAD_INGREDIENTES'])

        db.session.commit()
        flash(f'Ingrediente "{ingrediente.nome}" atualizado!', 'success')
        return redirect(url_for('admin_ingredientes'))

    return render_template('admin/ingredientes_form.html', form=form, ingrediente=ingrediente)


@app.route('/admin/ingredientes/excluir/<int:ingrediente_id>', methods=['POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_ingredientes_excluir(ingrediente_id):
    ingrediente = Ingrediente.query.get_or_404(ingrediente_id)
    remover_imagem(app.config['PASTA_UPLOAD_INGREDIENTES'], ingrediente.imagem)
    nome = ingrediente.nome
    db.session.delete(ingrediente)
    db.session.commit()
    flash(f'Ingrediente "{nome}" removido.', 'info')
    return redirect(url_for('admin_ingredientes'))


# — Pedidos —

@app.route('/admin/pedidos')
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_pedidos():
    status_filtro = request.args.get('status')
    consulta = Pedido.query
    if status_filtro:
        try:
            consulta = consulta.filter_by(status=StatusPedidoEnum[status_filtro])
        except KeyError:
            pass
    pedidos = consulta.order_by(Pedido.criado_em.desc()).all()
    return render_template('admin/pedidos_lista.html', pedidos=pedidos, status_opcoes=StatusPedidoEnum, status_filtro=status_filtro)


@app.route('/admin/pedidos/<int:pedido_id>', methods=['GET', 'POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_pedido_detalhe(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    form = StatusPedidoForm()
    form.status.choices = [(s.name, s.value) for s in StatusPedidoEnum]

    if request.method == 'GET':
        form.status.data = pedido.status.name

    if form.validate_on_submit():
        pedido.status = StatusPedidoEnum[form.status.data]
        db.session.commit()
        flash(f'Status do pedido #{pedido.id} atualizado para "{pedido.status.value}".', 'success')
        return redirect(url_for('admin_pedido_detalhe', pedido_id=pedido.id))

    return render_template('admin/pedido_detalhe_admin.html', pedido=pedido, form=form)


# — Configurações da loja —

@app.route('/admin/configuracoes', methods=['GET', 'POST'])
@login_required
@perfil_requerido(PerfilEnum.ADMIN)
def admin_configuracoes():
    config = Configuracao.query.first()
    if not config:
        config = Configuracao()
        db.session.add(config)
        db.session.commit()

    form = ConfiguracaoForm(obj=config)

    if form.validate_on_submit():
        form.populate_obj(config)
        db.session.commit()
        flash('Configurações da loja atualizadas!', 'success')
        return redirect(url_for('admin_configuracoes'))

    return render_template('admin/configuracoes.html', form=form)
