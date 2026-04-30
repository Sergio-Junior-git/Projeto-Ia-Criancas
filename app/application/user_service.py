from app.application.security import hash_password, verify_password


class UserService:
    def __init__(self, users):
        self.users = users

    def register(self, name, email, password):
        if len(password) < 6:
            raise ValueError("A senha precisa ter pelo menos 6 caracteres.")
        if self.users.get_by_email(email):
            raise ValueError("Ja existe uma conta com este e-mail.")
        return self.users.create(name, email, hash_password(password))

    def authenticate(self, email, password):
        user = self.users.get_by_email(email)
        if not user or not verify_password(user.password_hash, password):
            raise ValueError("E-mail ou senha invalidos.")
        return user
