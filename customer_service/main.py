import time
from functools import wraps

from flask import Flask
from flask import request
from flask import jsonify
from flask import Response

from datetime import timezone

from web3 import Web3
from solcx import compile_source, install_solc
from pathlib import Path

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

GANACHE_URL = application.config["WEB3_RPC"]
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

max_retries = 30
for i in range(max_retries):
    if w3.is_connected():
        print("Connected to Ganache")
        break
    print(f"Waiting for Ganache... ({i+1}/{max_retries})")
    time.sleep(1)
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
else:
    raise ConnectionError("Unable to connect to Ganache after 30s")


install_solc(application.config["SOLC_VERSION"])
sol_path = Path("blockchain/OrderContract.sol")
source = sol_path.read_text(encoding="utf-8")
compiled = compile_source(source, output_values=["abi", "bin"], solc_version=application.config["SOLC_VERSION"])
_, interface = compiled.popitem()
ABI = interface["abi"]
BYTECODE = interface["bin"]

owner_address = w3.eth.accounts[application.config["OWNER_ADDRESS_INDEX"]]
#customer_address = w3.eth.accounts[2]
courier_address = w3.eth.accounts[3]
#print(f"[Blockchain] Owner={owner_address}, Customer={customer_address}, Courier={courier_address}")


def handle_auth_errors(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            return jsonify({"msg": "Missing Authorization Header"}), 401
    return wrapper

@jwt.invalid_token_loader
def invalid_token_callback(err_msg):
    return jsonify({"msg": "Missing Authorization Header"}), 401

# Kad token expired
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"msg": "Missing Authorization Header"}), 401

# Kad token nedostaje
@jwt.unauthorized_loader
def missing_token_callback(err_msg):
    return jsonify({"msg": "Missing Authorization Header"}), 401

@application.route("/search", methods = ["GET"])
@jwt_required()
def search():
    claims = get_jwt()
    if claims["roles"][0] != "customer":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    name = ""
    category = ""
    if "name" in request.args:
        name = request.args.get("name")
    if "category" in request.args:
        category = request.args.get("category")
    print(category)
    query = database.session.query(Product, Category)\
        .join(ProductCategory, Product.id == ProductCategory.product_id)\
        .join(Category, ProductCategory.category_id == Category.id)\
        .filter(Product.name.like(f"%{name}%"))\
        .filter(Category.name.like(f"%{category}%"))

    '''Product.query.join(Product.categories)
            .filter(Product.name.like(f"%{name}%"))
            .filter(Category.name.like(f"%{category}"))'''
    categories = []
    products = []
    for product, category in query:
        if product not in products:
            products.append(product)
        for cat in product.categories:
            if cat.name not in categories:
                categories.append(cat.name)
    jsonproducts = []
    for product in products:
        jsonobject = {}
        cats = []
        for categ in product.categories:
            cats.append(categ.name)
        jsonobject["categories"] = cats
        jsonobject["id"] = product.id
        jsonobject["name"] = product.name
        jsonobject["price"] = product.price
        jsonproducts.append(jsonobject)
    return jsonify({"categories": categories, "products": jsonproducts}), 200

@application.route("/order", methods = ["POST"])
@jwt_required()
def order():
    claims = get_jwt()
    if claims["roles"][0] != "customer":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    requests = request.get_json()
    if requests is None:
        return jsonify({"message": "Field requests is missing."}), 400
    address = requests.get("address")
    requests = requests.get("requests")
    if requests is None or len(requests) == 0:
        return jsonify({"message": "Field requests is missing."}), 400
    counter = 0
    items = []
    last_order = database.session.query(Order).order_by(Order.id.desc()).first()
    next_id = 1 if last_order is None else last_order.id + 1

    order = Order(id = next_id, status = "CREATED", user_email = get_jwt_identity(), contract_address="X")
    database.session.add(order)
    price = 0
    #database.session.commit()
    for req in requests:
        id = req.get("id")
        quantity = req.get("quantity")
        if id is None:
            return jsonify({"message": f"Product id is missing for request number {counter}."}), 400
        if quantity is None:
            return jsonify({"message": f"Product quantity is missing for request number {counter}."}), 400
        try:
            id = int(id)
            if id <= 0:
                raise Exception
        except Exception as e:
            return jsonify({"message": f"Invalid product id for request number {counter}."}), 400
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise Exception
        except Exception as e:
            return jsonify({"message": f"Invalid product quantity for request number {counter}."}), 400
        product = Product.query.filter(Product.id == id).first()
        if product is None:
            return jsonify({"message": f"Invalid product for request number {counter}."}), 400
        counter += 1
        newItem = OrderItem(
            product_id = id,
            quantity = quantity,
            order = order
        )
        price += quantity * product.price
        database.session.add(newItem)
        #database.session.commit()
        items.append(newItem)
    if address is None or address == "":
        return jsonify({"message": f"Field address is missing."}), 400
    if not Web3.is_address(address):
        return jsonify({"message": f"Invalid address."}), 400
    contract = w3.eth.contract(abi=ABI, bytecode=BYTECODE)
    print("Deploying with amountWei =", int(price * 100))
    print("Owner:", owner_address)
    print("Customer:", address)
    tx_hash = contract.constructor(owner_address, address, int(price * 100)).transact({"from": owner_address,
                                                                                                "gas": 3000000})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = receipt.contractAddress
    order.contract_address = contract_address
    database.session.commit()
    return jsonify({"id": order.id}), 200

@application.route("/status", methods = ["GET"])
@jwt_required()
def status():
    claims = get_jwt()
    if claims["roles"][0] != "customer":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    email = get_jwt_identity()
    jsonOrdersList = []
    orderQuery = Order.query.filter(Order.user_email == email)
    for order in orderQuery:
        orderDict = {}
        productsList = []
        sumPrice = 0
        orderItemsQuery = OrderItem.query.filter(OrderItem.order_id == order.id)
        for orderItem in orderItemsQuery:
            product = orderItem.product
            categories = []
            for cat in product.categories:
                categories.append(cat.name)
            productsList.append({"categories": categories, "name": product.name,
                                 "price": product.price, "quantity": orderItem.quantity})
            sumPrice += product.price * orderItem.quantity
        jsonOrdersList.append({"products": productsList, "price": sumPrice,
                               "status": order.status,
                               "timestamp": order.timestamp.replace(tzinfo = timezone.utc).isoformat().replace("+00:00", "Z")})
    return jsonify({"orders": jsonOrdersList}), 200

@application.route("/delivered", methods = ["POST"])
@jwt_required()
def delivered():
    claims = get_jwt()
    if claims["roles"][0] != "customer":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    try:
        data = request.get_json()
    except Exception as e:
        print(e)
        return jsonify({"message": "Missing order id."}), 400
    if data is None or data.get("id") is None:
        return jsonify({"message": "Missing order id."}), 400
    id = data.get("id")
    try:
        id = int(id)
        if id <= 0:
            raise Exception
    except Exception as e:
        return jsonify({"message": "Invalid order id."}), 400
    order = Order.query.filter(Order.id == id).first()
    if order is None or order.user_email != get_jwt_identity():
        return jsonify({"message": "Invalid order id."}), 400
    if order.status == "COMPLETE":
        return jsonify({"message": "Invalid order id."}), 400
    contract = w3.eth.contract(address=order.contract_address, abi=ABI)
    if not contract.functions.isPickedUp().call():
        return jsonify({"message": "Delivery not complete."}), 400

    tx_hash = contract.functions.finaliseDelivery().transact({
        "from": owner_address,
        "gas": 3000000
    })
    w3.eth.wait_for_transaction_receipt(tx_hash)
    order.status = "COMPLETE"
    database.session.commit()
    return "", 200

@application.route("/generate_invoice", methods = ["POST"])
@jwt_required()
@handle_auth_errors
def generate_invoice():
    claims = get_jwt()
    if claims["roles"][0] != "customer":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    try:
        data = request.get_json()
    except Exception as e:
        print(e)
        return jsonify({"message": "Missing order id."}), 400
    if data is None or data.get("id") is None:
        return jsonify({"message": "Missing order id."}), 400
    id = data.get("id")
    try:
        id = int(id)
        if id <= 0:
            raise ValueError
    except:
        return jsonify({"message": "Invalid order id."}), 400
    order = Order.query.filter(Order.id == id).first()
    if order is None:
        return jsonify({"message": "Invalid order id."}), 400
    address = data.get("address")
    if address is None:
        return jsonify({"message": "Missing address."}), 400
    contract = w3.eth.contract(address=order.contract_address, abi=ABI)
    if not Web3.is_address(address):
        return jsonify({"message": "Invalid address."}), 400
    try:
        if Web3.to_checksum_address(address) != Web3.to_checksum_address(contract.functions.customer().call()):
            return jsonify({"message": "Invalid address."}), 400
    except:
        return jsonify({"message": "Invalid address."}), 400
    if contract.functions.isPaid().call():
        return jsonify({"message": "Transfer already complete."}), 400
    print(f"[DATA] Order ID: {id} Address: {address}")
    price = 0
    for item in OrderItem.query.filter(OrderItem.order_id == order.id).all():
        product = Product.query.filter(Product.id == item.product_id).first()
        price += product.price * item.quantity
    invoice = {
        "from": address,
        "to": order.contract_address,
        "value": int(price * 100),
        "gas": 3000000,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(address),
        "chainId": w3.eth.chain_id
    }
    print(f"Invoice {invoice} za order id: {id}")
    return jsonify({"invoice": invoice}), 200


if __name__ == '__main__':
    db_created = False
    while not db_created:
        try:
            with application.app_context():
                database.create_all()
                from sqlalchemy import text

                with database.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE `order` AUTO_INCREMENT = 1;"))
                    conn.commit()
            db_created = True
        except Exception as e:
            pass
    HOST = "0.0.0.0" if ("PRODUCTION" in os.environ) else "127.0.0.1"
    application.run(debug=True, host=HOST, port=5000)