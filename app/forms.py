from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, SubmitField, SelectField,
    DecimalField, TextAreaField, BooleanField, IntegerField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional


class CadastroForm(FlaskForm):
    nome = StringField('Nome completo', validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    endereco = StringField('Endereço de entrega', validators=[Optional(), Length(max=250)])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6, message='A senha precisa ter pelo menos 6 caracteres.')])
    confirmar_senha = PasswordField(
        'Confirmar senha',
        validators=[DataRequired(), EqualTo('senha', message='As senhas não coincidem.')]
    )
    submit = SubmitField('Criar conta')


class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')


class PizzaForm(FlaskForm):
    nome = StringField('Nome da pizza', validators=[DataRequired(), Length(max=120)])
    descricao = TextAreaField('Ingredientes / descrição', validators=[Optional(), Length(max=1000)])
    preco = DecimalField('Preço (R$)', validators=[DataRequired(), NumberRange(min=0)])
    categoria_id = SelectField('Categoria', coerce=int, validators=[DataRequired()])
    imagem = FileField('Imagem da pizza', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Envie apenas imagens (jpg, png, webp).')])
    ativo = BooleanField('Disponível no cardápio', default=True)
    submit = SubmitField('Salvar')


class IngredienteForm(FlaskForm):
    nome = StringField('Nome do ingrediente', validators=[DataRequired(), Length(max=120)])
    tipo = SelectField('Tipo', validators=[DataRequired()])
    preco = DecimalField('Preço adicional (R$)', validators=[DataRequired(), NumberRange(min=0)])
    imagem = FileField('Imagem', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Envie apenas imagens (jpg, png, webp).')])
    ativo = BooleanField('Disponível para montagem', default=True)
    submit = SubmitField('Salvar')


class CategoriaForm(FlaskForm):
    nome = StringField('Nome da categoria', validators=[DataRequired(), Length(max=80)])
    submit = SubmitField('Adicionar categoria')


class ConfiguracaoForm(FlaskForm):
    nome_loja = StringField('Nome da loja', validators=[DataRequired(), Length(max=150)])
    endereco = StringField('Endereço completo', validators=[DataRequired(), Length(max=250)])
    telefone = StringField('Telefone', validators=[DataRequired(), Length(max=20)])
    whatsapp = StringField('WhatsApp (só números, com DDD)', validators=[Optional(), Length(max=20)])
    horario_funcionamento = StringField('Horário de funcionamento', validators=[DataRequired(), Length(max=150)])
    latitude = DecimalField('Latitude', validators=[DataRequired()], places=6)
    longitude = DecimalField('Longitude', validators=[DataRequired()], places=6)
    preco_base_montagem = DecimalField('Preço base da massa (Monte sua Pizza)', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Salvar configurações')


class StatusPedidoForm(FlaskForm):
    status = SelectField('Status do pedido', validators=[DataRequired()])
    submit = SubmitField('Atualizar status')


class CheckoutForm(FlaskForm):
    endereco_entrega = StringField('Endereço de entrega', validators=[DataRequired(), Length(max=250)])
    forma_pagamento = SelectField(
        'Forma de pagamento',
        choices=[('Dinheiro', 'Dinheiro'), ('Cartão na entrega', 'Cartão na entrega'), ('Pix', 'Pix')],
        validators=[DataRequired()]
    )
    observacoes = TextAreaField('Observações (opcional)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Confirmar pedido')


class MontarPizzaForm(FlaskForm):
    """Usado apenas para gerar o token CSRF na página de montar pizza."""
    submit = SubmitField('Adicionar ao carrinho')
