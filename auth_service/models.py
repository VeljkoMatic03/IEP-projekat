from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy()

class UserRole(database.Model):
    id = database.Column(database.Integer, primary_key = True)
    user_id = database.Column(database.Integer, database.ForeignKey("user.id"), nullable = False)
    role_id = database.Column(database.Integer, database.ForeignKey("role.id"), nullable = False)

class User(database.Model):
    id = database.Column(database.Integer, primary_key = True)
    email = database.Column(database.String(256), nullable = False, unique = True)
    password = database.Column(database.String(256), nullable = False)
    forename = database.Column(database.String(256), nullable = False)
    surname = database.Column(database.String(256), nullable = False)

    roles = database.relationship("Role", secondary = UserRole.__table__, back_populates = "users")

class Role(database.Model):
    id = database.Column(database.Integer, primary_key = True)
    name = database.Column(database.String(256), nullable = False)

    users = database.relationship("User", secondary = UserRole.__table__, back_populates = "roles")