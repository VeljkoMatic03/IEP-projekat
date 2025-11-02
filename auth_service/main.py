from functools import wraps

from flask import Flask
from flask import request
from flask import jsonify
from flask import Response

import re

from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity, get_jwt

from configuration import Configuration
import os

from models import database
from models import User
from models import Role
from models import UserRole

application = Flask(__name__)
application.config.from_object(Configuration)
database.init_app(application)

@application.route("/register_customer", methods = ["POST"])
def register_customer():
    role = Role.query.filter(Role.name == "customer").first()
    data = request.get_json()
    if data is None:
        return jsonify({"message": "Field forename is missing."}), 400
    jsonforename = data.get("forename")
    if jsonforename is None or jsonforename == "":
        return jsonify({"message": "Field forename is missing."}), 400
    jsonsurname = data.get("surname")
    if jsonsurname is None or jsonsurname == "":
        return jsonify({"message": "Field surname is missing."}), 400
    jsonemail = data.get("email")
    if jsonemail is None or jsonemail == "":
        return jsonify({"message": "Field email is missing."}), 400
    jsonpassword = data.get("password")
    if jsonpassword is None or jsonpassword == "":
        return jsonify({"message": "Field password is missing."}), 400
    regexPattern = r"^[a-zA-Z0-9_.]+\@[a-z]+\.[a-z]{2,}$"
    search = re.search(regexPattern, jsonemail)
    if search is None:
        return jsonify({"message": "Invalid email."}), 400
    print(search)
    if len(jsonpassword) < 8:
        return jsonify({"message": "Invalid password."}), 400
    if User.query.filter(User.email == jsonemail).first() != None:
        return jsonify({"message": "Email already exists."}), 400
    newUser = User(
        email = jsonemail,
        password = jsonpassword,
        forename = jsonforename,
        surname = jsonsurname
    )
    database.session.add(newUser)
    database.session.commit()
    newUserRole = UserRole(
        user_id = newUser.id,
        role_id = role.id
    )
    database.session.add(newUserRole)
    database.session.commit()
    return Response(status = 200)

@application.route("/register_courier", methods = ["POST"])
def register_courier():
    role = Role.query.filter(Role.name == "courier").first()
    data = request.get_json()
    if data is None:
        return jsonify({"message": "Field forename is missing."}), 400
    jsonforename = data.get("forename")
    if jsonforename is None or jsonforename == "":
        return jsonify({"message": "Field forename is missing."}), 400
    jsonsurname = data.get("surname")
    if jsonsurname is None or jsonsurname == "":
        return jsonify({"message": "Field surname is missing."}), 400
    jsonemail = data.get("email")
    if jsonemail is None or jsonemail == "":
        return jsonify({"message": "Field email is missing."}), 400
    jsonpassword = data.get("password")
    if jsonpassword is None or jsonpassword == "":
        return jsonify({"message": "Field password is missing."}), 400
    regexPattern = r"^[a-zA-Z0-9_.]+\@[a-z]+\.[a-z]{2,}$"
    search = re.search(regexPattern, jsonemail)
    if search is None:
        return jsonify({"message": "Invalid email."}), 400
    print(search)
    if len(jsonpassword) < 8:
        return jsonify({"message": "Invalid password."}), 400
    if User.query.filter(User.email == jsonemail).first() != None:
        return jsonify({"message": "Email already exists."}), 400
    newUser = User(
        email = jsonemail,
        password = jsonpassword,
        forename = jsonforename,
        surname = jsonsurname
    )
    database.session.add(newUser)
    database.session.commit()
    newUserRole = UserRole(
        user_id = newUser.id,
        role_id = role.id
    )
    database.session.add(newUserRole)
    database.session.commit()
    return Response(status = 200)

jwt = JWTManager(application)

@application.route("/login", methods = ["POST"])
def login():
    data = request.get_json()
    if data is None:
        return jsonify({"message": "Field email is missing."}), 400
    jsonemail = data.get("email")
    if jsonemail is None or jsonemail == "":
        return jsonify({"message": "Field email is missing."}), 400
    jsonpassword = data.get("password")
    if jsonpassword is None or jsonpassword == "":
        return jsonify({"message": "Field password is missing."}), 400
    regexPattern = r"^[a-zA-Z0-9_.]+\@[a-z]+\.[a-z]{2,}$"
    search = re.search(regexPattern, jsonemail)
    if search is None:
        return jsonify({"message": "Invalid email."}), 400
    user = User.query.filter(User.email == jsonemail, User.password == jsonpassword).first()
    if not user:
        return jsonify({"message": "Invalid credentials."}), 400
    claims = {
        "forename": user.forename,
        "surname": user.surname,
        "roles": [role.name for role in user.roles]
    }
    access_token = create_access_token(identity=user.email, additional_claims=claims)
    return jsonify({"accessToken": access_token}), 200

def handle_auth_errors(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            return jsonify({"msg": "Missing Authorization Header"}), 401
    return wrapper

@application.route("/delete", methods = ["POST"])
@jwt_required()
@handle_auth_errors
def delete():
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims["roles"]
    user = User.query.filter(User.email == identity).first()
    if not user:
        return jsonify({"message": "Unknown user."}), 400
    userRole = UserRole.query.filter(UserRole.user_id == user.id).first()
    database.session.delete(userRole)
    database.session.commit()
    database.session.delete(user)
    database.session.commit()
    return "", 200


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    db_created = False
    while not db_created:
        try:
            with application.app_context():
                database.create_all()
                owner_role = Role.query.filter(Role.name == "owner").first()
                courir_role = Role.query.filter(Role.name == "courier").first()
                customer_role = Role.query.filter(Role.name == "customer").first()

                if (owner_role is None):
                    owner_role = Role(name="owner")
                    database.session.add(owner_role)

                if (courir_role is None):
                    database.session.add(Role(name="courier"))

                if (customer_role is None):
                    database.session.add(Role(name="customer"))

                scrooge = User.query.filter(User.email == "onlymoney@gmail.com").first()
                if scrooge is None:
                    scrooge = User(forename="Scrooge", surname="McDuck",
                                              email="onlymoney@gmail.com", password="evenmoremoney")
                    userrole = UserRole(user_id=scrooge.id, role_id = owner_role.id)
                    database.session.add(scrooge)
                    database.session.add(userrole)

                database.session.commit()
            db_created = True
        except Exception as e:
            pass
    HOST = "0.0.0.0" if ("PRODUCTION" in os.environ) else "127.0.0.1"
    application.run(debug = True, host=HOST, port=5000)
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
