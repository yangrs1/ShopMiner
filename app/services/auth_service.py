import re
from app.models.user import User
from app.extensions import db
from flask_jwt_extended import create_access_token

PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$')


def register_user(email, password, first_name, last_name, address="", icon="icon_bear.png"):
    if User.query.filter_by(email=email).first():
        return None, "Email already registered"

    if not PASSWORD_REGEX.match(password):
        return None, "Password must be at least 8 characters with uppercase, lowercase and digit"

    user = User(
        first_name=first_name,
        last_name=last_name,
        address=address,
        email=email,
        icon=icon,
        balance=0,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, None


def authenticate_user(email, password):
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return None
    return user


def get_user_by_id(user_id):
    return db.session.get(User, user_id)


def generate_token(user):
    return create_access_token(identity=str(user.id))
