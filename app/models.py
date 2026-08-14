import enum
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class PerfilEnum(enum.Enum):
    CLIENTE = "cliente"
    ADMIN = "admin"


class StatusPedidoEnum(enum.Enum):
    PENDENTE = "Pendente"
    EM_PREPARO = "Em preparo"
    SAIU_PARA_ENTREGA = "Saiu para entrega"
    ENTREGUE = "Entregue"
    CANCELADO = "Cancelado"


class TipoIngredienteEnum(enum.Enum):
    MOLHO = "Molho"
    QUEIJO = "Queijo"
    CARNE = "Carne"
    FRUTOS_DO_MAR = "Frutos do Mar"
    VEGETAL = "Vegetal"
    ESPECIAL = "Especial"
    BORDA = "Borda Recheada"


# ── Usuário ──────────────────────────────────────────────────────────────────

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.String(250))
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.Enum(PerfilEnum), default=PerfilEnum.CLIENTE, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    pedidos = db.relationship('Pedido', backref='usuario', lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f'<Usuario {self.email}>'


# ── Cardápio ─────────────────────────────────────────────────────────────────

class CategoriaPizza(db.Model):
    __tablename__ = 'categorias_pizza'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)

    pizzas = db.relationship('Pizza', backref='categoria', lazy=True)


class Pizza(db.Model):
    __tablename__ = 'pizzas'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text)
    preco = db.Column(db.Numeric(8, 2), nullable=False)
    imagem = db.Column(db.String(255))
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_pizza.id'))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def preco_formatado(self):
        return f'R$ {self.preco:.2f}'.replace('.', ',')


class Ingrediente(db.Model):
    __tablename__ = 'ingredientes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.Enum(TipoIngredienteEnum), nullable=False)
    preco = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    imagem = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def preco_formatado(self):
        return f'R$ {self.preco:.2f}'.replace('.', ',')


# ── Pedidos ──────────────────────────────────────────────────────────────────

class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    status = db.Column(db.Enum(StatusPedidoEnum), default=StatusPedidoEnum.PENDENTE, nullable=False)
    endereco_entrega = db.Column(db.String(250))
    forma_pagamento = db.Column(db.String(50))
    observacoes = db.Column(db.Text)
    total = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    itens = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade='all, delete-orphan')

    def total_formatado(self):
        return f'R$ {self.total:.2f}'.replace('.', ',')


class ItemPedido(db.Model):
    __tablename__ = 'itens_pedido'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    pizza_id = db.Column(db.Integer, db.ForeignKey('pizzas.id'), nullable=True)
    nome = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='cardapio')  # cardapio | montada
    preco_unitario = db.Column(db.Numeric(8, 2), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Numeric(8, 2), nullable=False)

    ingredientes = db.relationship('ItemPedidoIngrediente', backref='item', lazy=True, cascade='all, delete-orphan')
    pizza = db.relationship('Pizza')

    def subtotal_formatado(self):
        return f'R$ {self.subtotal:.2f}'.replace('.', ',')

    def preco_unitario_formatado(self):
        return f'R$ {self.preco_unitario:.2f}'.replace('.', ',')


class ItemPedidoIngrediente(db.Model):
    __tablename__ = 'itens_pedido_ingredientes'

    id = db.Column(db.Integer, primary_key=True)
    item_pedido_id = db.Column(db.Integer, db.ForeignKey('itens_pedido.id'), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    preco = db.Column(db.Numeric(8, 2), nullable=False, default=0)


# ── Configuração da loja ─────────────────────────────────────────────────────

class Configuracao(db.Model):
    __tablename__ = 'configuracao'

    id = db.Column(db.Integer, primary_key=True)
    nome_loja = db.Column(db.String(150), default='Bella Fatia Pizzaria')
    endereco = db.Column(db.String(250), default='Av. Principal, 123 - Centro')
    telefone = db.Column(db.String(20), default='(75) 99999-9999')
    whatsapp = db.Column(db.String(20))
    horario_funcionamento = db.Column(db.String(150), default='Terça a Domingo, 18h às 23h30')
    latitude = db.Column(db.Float, default=-12.2664)
    longitude = db.Column(db.Float, default=-38.9663)
    preco_base_montagem = db.Column(db.Numeric(8, 2), default=22.00)
