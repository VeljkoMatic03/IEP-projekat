from functools import wraps

from flask import Flask
from flask import request
from flask import jsonify
from flask import Response
from flask_jwt_extended.exceptions import JWTExtendedException

from sqlalchemy import func, case

from models import Product, Category, ProductCategory, Order, OrderItem

import re

from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity, get_jwt

from configuration import Configuration
import os

from models import database

application = Flask(__name__)
application.config.from_object(Configuration)
database.init_app(application)
jwt = JWTManager(application)

@application.route("/ping")
def ping():
    return "ping", 200

def handle_auth_errors(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            return jsonify({"msg": "Missing Authorization Header"}), 401
    return wrapper


@application.route("/update", methods = ["POST"])
@jwt_required()
@handle_auth_errors
def update():
    try:
        claims = get_jwt()
    except Exception as e:
        print(e)
        return jsonify({"msg": "Missing Authorization Header"}), 401
    if claims["roles"][0] != "owner":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    try:
        file = request.files.get("file")
    except Exception as e:
        print(e)
        return jsonify({"message": "Field file is missing."}), 400
    if file is None or file.filename == "":
        return jsonify({"message": "Field file is missing."}), 400
    content = file.stream.read().decode()
    count = 0
    for line in content.split("\n"):
        data = line.split(",")
        if len(data) != 3:
            return jsonify({"message": f"Incorrect number of values on line {count}."}), 400
        count += 1
    count = 0
    for line in content.split("\n"):
        data = line.split(",")
        try:
            price = float(data[2])
            if price < 0:
                return jsonify({"message": f"Incorrect price on line {count}."}), 400
        except Exception as e:
            return jsonify({"message": f"Incorrect price on line {count}."}), 400
        count += 1
    count = 0
    for line in content.split("\n"):
        data = line.split(",")
        name = data[1]
        price = float(data[2])
        try:

            if not Product.query.filter(Product.name == name).first() is None:
                return jsonify({"message": f"Product {name} already exists."}), 400
        except Exception as e:
            print(e)
            return "ERROR", 404
        categories = data[0].split("|")
        count += 1
        print(*categories)
        newProduct = Product(
            name = name,
            price = price
        )
        database.session.add(newProduct)
        database.session.commit()
        for cat in categories:
            category = Category.query.filter(Category.name == cat).first()
            if category is None:
                category = Category(
                    name = cat
                )
                database.session.add(category)
                database.session.commit()
                category = Category.query.filter(Category.name == cat).first()
            newPC = ProductCategory(
                product_id = newProduct.id,
                category_id = category.id
            )
            database.session.add(newPC)
            database.session.commit()
    return "", 200

@application.route("/product_statistics", methods = ["GET"])
@jwt_required()
@handle_auth_errors
def product_statistics():
    claims = get_jwt()
    if claims["roles"][0] != "owner":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    statistics = []
    print("SAD")
    try:
        query = (database.session.query(Product.name,
            func.sum(case((Order.status == 'COMPLETE', OrderItem.quantity), else_ = 0)).label('completed'),
            func.sum(case((Order.status != 'COMPLETE', OrderItem.quantity), else_ = 0)).label('not_complete'))
            .join(OrderItem, Product.id == OrderItem.product_id)
            .join(Order, OrderItem.order_id == Order.id)
            .group_by(Product.id)
        )
    except Exception as e:
        print(e)
        return "ERROR", 404
    for name, completed, not_completed in query.all():
        print(name, completed, not_completed)
        statistics.append({"name": name, "sold": int(completed), "waiting": int(not_completed)})
    return jsonify({"statistics": statistics}), 200

@application.route("/category_statistics", methods = ["GET"])
@jwt_required()
@handle_auth_errors
def category_statistics():
    claims = get_jwt()
    if claims["roles"][0] != "owner":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    try:
        param = func.sum(case((Order.status == 'COMPLETE', OrderItem.quantity), else_=0)).label('sum')
        query = (
            database.session.query(Category.name,
               #func.sum(case(Order.status == 'COMPLETED', OrderItem.quantity), else_=0).label('sum')
                param
            )
            .outerjoin(ProductCategory, Category.id == ProductCategory.category_id)
            .outerjoin(Product, Product.id == ProductCategory.product_id)
            .outerjoin(OrderItem, OrderItem.product_id == Product.id)
            .outerjoin(Order, Order.id == OrderItem.order_id)
            .group_by(Category.id)
            .order_by(param.desc())
            .order_by(Category.name)
        )
    except Exception as e:
        print(e)
        return "ERROR", 404
    statistics = []
    for name, sum in query.all():
        print(name, sum)
        statistics.append(name)
    return jsonify({"statistics": statistics}), 200


if __name__ == '__main__':
    db_created = False
    while not db_created:
        try:
            with application.app_context():
                database.create_all()
            db_created = True
        except Exception as e:
            pass
    HOST = "0.0.0.0" if ("PRODUCTION" in os.environ) else "127.0.0.1"
    application.run(debug=True, host=HOST, port=5000)