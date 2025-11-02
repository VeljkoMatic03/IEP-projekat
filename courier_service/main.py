import time
from functools import wraps

from flask import Flask
from flask import request
from flask import jsonify
from flask import Response

from sqlalchemy import func, case

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

owner_address = w3.eth.accounts[application.config["OWNER_ADDRESS_INDEX"]]

def handle_auth_errors(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            return jsonify({"msg": "Missing Authorization Header"}), 401
    return wrapper

@application.route('/orders_to_deliver', methods = ['GET'])
@jwt_required()
@handle_auth_errors
def orders_to_deliver():
    claims = get_jwt()
    if claims["roles"][0] != "courier":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    orders = []
    query = database.session.query(Order.id, Order.user_email).filter(Order.status == 'CREATED')
    for id, email in query.all():
        orders.append({"id": id, "email": email})
    return jsonify({"orders": orders}), 200

@application.route('/pick_up_order', methods = ['POST'])
@jwt_required()
@handle_auth_errors
def pick_up_order():
    claims = get_jwt()
    if claims["roles"][0] != "courier":
        return jsonify({"msg": "Missing Authorization Header"}), 401
    data = request.get_json()
    if data is None:
        return jsonify({"message": "Missing order id."}), 400
    id = data.get("id")
    if id is None:
        return jsonify({"message": "Missing order id."}), 400
    try:
        id = int(id)
        if id <= 0:
            return jsonify({"message": "Invalid order id."}), 400
    except Exception as e:
        return jsonify({"message": "Invalid order id."}), 400
    order = Order.query.filter(Order.id == id).first()
    if order is None or order.status != 'CREATED':
        return jsonify({"message": "Invalid order id."}), 400
    address = data.get("address")
    if address is None or address == "":
        return jsonify({"message": f"Field address is missing."}), 400
    if not Web3.is_address(address):
        return jsonify({"message": f"Invalid address."}), 400
    contract = w3.eth.contract(address=order.contract_address, abi=ABI)
    if not contract.functions.isPaid().call():
        return jsonify({"message": "Transfer not complete."}), 400
    order.status = 'PENDING'
    tx_hash = contract.functions.pickUp(address).transact({
        "from": owner_address,
        "gas": 3000000
    })
    w3.eth.wait_for_transaction_receipt(tx_hash)
    database.session.commit()
    return "", 200


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