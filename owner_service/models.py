from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

database = SQLAlchemy()

class ProductCategory(database.Model):

    id = database.Column(database.Integer, primary_key = True)
    product_id = database.Column(database.Integer, database.ForeignKey("product.id"), nullable = False)
    category_id = database.Column(database.Integer, database.ForeignKey("category.id"), nullable = False)

class Product(database.Model):

    id = database.Column(database.Integer, primary_key = True)
    name = database.Column(database.String(256), nullable = False)
    price = database.Column(database.Float, nullable = False)
    categories = database.relationship("Category", secondary = ProductCategory.__table__, back_populates = "products")

class Category(database.Model):

    id = database.Column(database.Integer, primary_key = True)
    name = database.Column(database.String(256), nullable=False)
    products = database.relationship("Product", secondary = ProductCategory.__table__, back_populates = "categories")

class Order(database.Model):

    id = database.Column(database.Integer, primary_key = True)
    status = database.Column(database.String(20), nullable = False)
    timestamp = database.Column(database.DateTime, nullable = False, default = datetime.utcnow())
    user_email = database.Column(database.String(256), nullable = False)
    contract_address = database.Column(database.String(42), nullable = False)

    items = database.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(database.Model):

    id = database.Column(database.Integer, primary_key=True)
    product_id = database.Column(database.Integer, database.ForeignKey("product.id"), nullable = False)
    quantity = database.Column(database.Integer, nullable = False)
    order_id = database.Column(database.Integer, database.ForeignKey("order.id"), nullable = False)

    order = database.relationship("Order", back_populates="items")
    product = database.relationship("Product")