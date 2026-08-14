"""
Script para criar (ou promover) um usuário administrador da pizzaria.
Rode com: python create_admin.py
"""
from getpass import getpass

from app import app, db
from app.models import Usuario, PerfilEnum


def main():
    with app.app_context():
        print('=== Criar usuário administrador ===')
        nome = input('Nome completo: ').strip()
        email = input('E-mail: ').strip().lower()

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            usuario.perfil = PerfilEnum.ADMIN
            if nome:
                usuario.nome = nome
            db.session.commit()
            print(f'\nUsuário existente "{email}" agora é administrador.')
            return

        senha = getpass('Senha (mínimo 6 caracteres): ')
        confirmar = getpass('Confirme a senha: ')

        if senha != confirmar:
            print('\nAs senhas não coincidem. Operação cancelada.')
            return
        if len(senha) < 6:
            print('\nA senha precisa ter pelo menos 6 caracteres. Operação cancelada.')
            return

        novo_admin = Usuario(nome=nome, email=email, perfil=PerfilEnum.ADMIN)
        novo_admin.set_senha(senha)
        db.session.add(novo_admin)
        db.session.commit()

        print(f'\nAdministrador "{nome}" ({email}) criado com sucesso!')


if __name__ == '__main__':
    main()
