#   _        _   _     _       _                       __  __  ____
#  | |      (_) | |   | |     (_)                     |  \/  |/ __ \
#  | |       _  | |_  | |__    _   _   _   _ __ ___   | \  / | |  | |
#  | |      | | | __| | "_ \  | | | | | | | "_ ` _ \  | |\/| | |  | |
#  | |____  | | | |_  | | | | | | | |_| | | | | | | | | |  | | |__| |
#  |______| |_|  \__| |_| |_| |_|  \__,_| |_| |_| |_| |_|  |_|\___\_\
from base64 import b64decode
from enum import Enum
from binascii import Error as DecErr

from typing import ClassVar, TypedDict

from flask import Blueprint, redirect, abort, \
    make_response, request, jsonify, Response
from flask_login import login_required, logout_user, login_user, \
    current_user, LoginManager

from forms import RegisterForm, LoginForm, ChangeUsernameForm, \
    ChangeEmailForm
from storage.user import User

MIN_PATH_LENGTH = 2


class UserJson(TypedDict):
    id: int
    username: str
    email: str


class UserResponseJson(TypedDict):
    auth: bool
    user: UserJson
    path: str


class FormMessage(Enum):
    Ok = ""
    EmailError = "Bad email"
    UsernameError = "Bad username"
    UsernameTooLongError = "Username too long"
    PasswordError = "Bad password"
    UserError = "Bad user"


def confirm_form(form: LoginForm) -> FormMessage:
    if not form.email.data:
        return FormMessage.EmailError.value

    if not form.password.data:
        return FormMessage.PasswordError.value

    return FormMessage.Ok.value


def confirm_username_form(form: ChangeUsernameForm) -> FormMessage:
    if not form.new_username.data:
        return FormMessage.UsernameError.value
    if len(form.new_username.data) > 40:
        return FormMessage.UsernameTooLongError.value
    return FormMessage.Ok.value


def get_path(encoded_path: str or bytes or None) -> str:
    if not encoded_path:
        return "/"
    try:
        loc = b64decode(encoded_path).decode()
        if len(loc) < MIN_PATH_LENGTH or (not loc.startswith("/")):
            return "/"
        return loc
    except (DecErr, UnicodeDecodeError):
        return "/"


def get_user_json(user: User) -> UserJson:
    return UserJson(
        id=user.id,
        username=user.username,
        email=user.email
    )


def create_handler(sess_cr: ClassVar, lm: LoginManager) -> Blueprint:
    """
    A closure for instantiating the handler that maintains main page.
    Must borrow a SqlAlchemy session creator for further usage.

    """

    app = Blueprint("user", __name__)

    @lm.user_loader
    def load_user(user_id: int):
        """ Function for loading the user """

        session = sess_cr()
        user = session.query(User).get(user_id)
        session.close()
        return user

    @app.after_request
    def allow_cors(response: Response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    @app.route("/do/get_user", methods=["GET"])
    def get_user():
        if current_user.is_authenticated:
            return jsonify(UserResponseJson(
                auth=True, user=get_user_json(current_user),
                path='/'))

        return jsonify(UserResponseJson(auth=False, user={}, path='/'))

    @app.route("/do/register", methods=["POST"])
    def register():
        """ Handler for register """
        form = RegisterForm()

        if form.password.data != form.password_again.data:
            return abort(make_response(
                {'message': 'Passwords do not match'}, 401))

        session = sess_cr()

        if session.query(User).filter(
                User.email == form.email.data).first():
            return abort(make_response(
                {'message': 'User with this email already exists'},
                409))

        # noinspection PyArgumentList
        user = User(
            email=form.email.data,
            username=form.username.data
        )

        user.set_password(form.password.data)
        session.add(user)
        session.commit()

        return {"status": True, "path": "/login"}

    @app.route("/do/login", methods=["POST"])
    def login():
        """ Handler for login """
        form = LoginForm()
        error_message = confirm_form(form)
        if error_message != FormMessage.Ok.value:
            return abort(make_response({'message': error_message}, 400))

        session = sess_cr()
        user = session.query(
            User).filter(User.email == form.email.data).first()

        # TODO Сделать ошибки информативными
        if not user:
            return abort(make_response(
                {'message': FormMessage.UserError.value}, 403))

        if not user.check_password(form.password.data):
            return abort(make_response(
                {'message': FormMessage.PasswordError.value}, 403))

        login_user(user)

        path = get_path(request.args.get("path", None))

        return jsonify(UserResponseJson(
            auth=True, user=get_user_json(current_user),
            path=path))

    @app.route("/do/change_username", methods=["POST"])
    @login_required
    def do_change_username():
        form = ChangeUsernameForm()

        error_message = confirm_username_form(form)
        if error_message != FormMessage.Ok.value:
            return abort(make_response({"message": error_message}, 401))
        session = sess_cr()

        user = session.query(User).filter(
            User.id == current_user.id).first()
        if not user:
            return abort(make_response({"message": "Invalid user"}))

        user.username = form.new_username.data
        session.commit()
        return jsonify(UserResponseJson(
            auth=True, user=get_user_json(user), path=''))

    @app.route("/do/change_email", methods=["POST"])
    @login_required
    def do_change_email():
        """ E-mail changing handler. """
        form = ChangeEmailForm()
        email = form.new_email.data
        password = form.password.data

        session = sess_cr()

        # User validation

        user = session.query(User).filter(
            User.id == current_user.id).first()
        if not user:
            return abort(make_response(
                {"message": "Invalid user"}, 401))

        if not user.check_password(password):
            return abort(make_response(
                {"message": "Invalid password"}, 401))

        if session.query(User).filter(User.email == email).first():
            return abort(make_response(
                {"message": "Email already exist"}, 401))

        user.email = email
        session.commit()

        return jsonify(UserResponseJson(auth=True,
                                        user=get_user_json(user),
                                        path=''))

    @app.route("/do/logout", methods=["POST"])
    @login_required
    def logout():
        """ Handler for logging out """

        logout_user()
        return redirect("/")

    return app
