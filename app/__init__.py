import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

app = Flask(__name__)

app.config['SECRET_KEY'] = 'pizzaria-bella-fatia-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pizzaria.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB por upload

app.config['PASTA_UPLOAD_PIZZAS'] = os.path.join(app.root_path, 'static', 'uploads', 'pizzas')
app.config['PASTA_UPLOAD_INGREDIENTES'] = os.path.join(app.root_path, 'static', 'uploads', 'ingredientes')
os.makedirs(app.config['PASTA_UPLOAD_PIZZAS'], exist_ok=True)
os.makedirs(app.config['PASTA_UPLOAD_INGREDIENTES'], exist_ok=True)

db.init_app(app)
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para continuar.'
login_manager.login_message_category = 'warning'

migrate = Migrate(app, db)


from app import models
from app import auth
from app import routes


CATEGORIAS_PADRAO = ['Tradicionais', 'Especiais', 'Doces', 'Bebidas']

TIPOS_INGREDIENTE_PADRAO_SEED = [
    ('Massa e Molho Base', [('Molho de Tomate', 0), ('Molho Branco', 2), ('Molho Barbecue', 2)]),
]

with app.app_context():
    db.create_all()

    nomes_existentes = {c.nome.lower() for c in models.CategoriaPizza.query.all()}
    for nome in CATEGORIAS_PADRAO:
        if nome.lower() not in nomes_existentes:
            db.session.add(models.CategoriaPizza(nome=nome))

    if models.Configuracao.query.count() == 0:
        db.session.add(models.Configuracao(
            nome_loja='Bella Fatia Pizzaria',
            endereco='Av. Presidente Dutra, 456 - Centro, Feira de Santana - BA',
            telefone='(75) 3221-4455',
            whatsapp='75999998888',
            horario_funcionamento='Terça a Domingo, das 18h às 23h30',
            latitude=-12.2664,
            longitude=-38.9663,
            preco_base_montagem=22.00
        ))

    db.session.commit()
