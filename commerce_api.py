# commerce_api.py
from __future__ import annotations
from datetime import datetime
import os

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError, fields, validates
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError


app = Flask(__name__)

# Database URI, use env var DATABASE_URI or fallback to localhost
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URI",
    "mysql+mysqlconnector://ecom_user:123123@localhost/ecommerce_api"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

# ------------ MODELS ------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    orders = db.relationship("Order", back_populates="user", cascade="all, delete-orphan")

class OrderProduct(db.Model):
    __tablename__ = "order_product"
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), primary_key=True)
    __table_args__ = (UniqueConstraint("order_id", "product_id", name="uq_order_product"),)

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", back_populates="orders")
    products = db.relationship("Product", secondary="order_product", back_populates="orders")

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    orders = db.relationship("Order", secondary="order_product", back_populates="products")

# ------------ SCHEMAS ------------

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_fk = True
    @validates("email")
    def validate_email(self, value, **kwargs):
        if "@" not in value:
            raise ValidationError("Invalid email format.")

class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True
        include_fk = True
    @validates("price")
    def validate_price(self, value, **kwargs):
        try:
            v = float(value)
        except Exception:
            raise ValidationError("Price must be numeric.")
        if v < 0:
            raise ValidationError("Price cannot be negative.")

class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        load_instance = True
        include_fk = True
    products = fields.Nested(ProductSchema, many=True, dump_only=True)
    @validates("user_id")
    def validate_user_id(self, value, **kwargs):
        if not User.query.get(value):
            raise ValidationError("user_id does not reference a real user.")

user_schema = UserSchema()
users_schema = UserSchema(many=True)
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

# ------------ ERRORS ------------

@app.errorhandler(ValidationError)
def on_validation(err):
    return jsonify({"error": err.messages}), 400

@app.errorhandler(404)
def on_404(err):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(IntegrityError)
def on_integrity_error(err):
    # most common case: UNIQUE constraint failed (e.g., duplicate email)
    db.session.rollback()
    return jsonify({"error": "Integrity error", "details": "Duplicate or invalid data"}), 400


# ------------ USERS ------------

@app.get("/users")
def get_users():
    return jsonify(users_schema.dump(User.query.all()))

@app.get("/users/<int:user_id>")
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user_schema.dump(user))

@app.post("/users")
def create_user():
    data = request.get_json() or {}
    user = user_schema.load(data)
    db.session.add(user)
    db.session.commit()
    return jsonify(user_schema.dump(user)), 201

@app.put("/users/<int:user_id>")
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    if "name" in data:
        user.name = data["name"]
    if "address" in data:
        user.address = data["address"]
    if "email" in data:
        user_schema.validate({"email": data["email"]})
        existing = User.query.filter(User.email == data["email"], User.id != user.id).first()
        if existing:
            return jsonify({"error": "Email already in use"}), 400
        user.email = data["email"]
    db.session.commit()
    return jsonify(user_schema.dump(user))

@app.delete("/users/<int:user_id>")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"})

# ------------ PRODUCTS ------------

@app.get("/products")
def get_products():
    return jsonify(products_schema.dump(Product.query.all()))

@app.get("/products/<int:product_id>")
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product_schema.dump(product))

@app.post("/products")
def create_product():
    data = request.get_json() or {}
    product = product_schema.load(data)
    db.session.add(product)
    db.session.commit()
    return jsonify(product_schema.dump(product)), 201

@app.put("/products/<int:product_id>")
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json() or {}
    if "product_name" in data:
        product.product_name = data["product_name"]
    if "price" in data:
        product_schema.validate({"price": data["price"]})
        product.price = float(data["price"])
    db.session.commit()
    return jsonify(product_schema.dump(product))

@app.delete("/products/<int:product_id>")
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})

# ------------ ORDERS ------------

@app.post("/orders")
def create_order():
    data = request.get_json() or {}
    order_date = (
        datetime.strptime(data["order_date"], "%Y-%m-%d %H:%M:%S")
        if data.get("order_date") else datetime.utcnow()
    )
    order = order_schema.load({"user_id": data.get("user_id"), "order_date": order_date})
    db.session.add(order)
    db.session.commit()
    return jsonify(order_schema.dump(order)), 201

@app.put("/orders/<int:order_id>/add_product/<int:product_id>")
def add_product_to_order(order_id, product_id):
    order = Order.query.get_or_404(order_id)
    product = Product.query.get_or_404(product_id)
    if product in order.products:
        return jsonify({"message": "Product already in order"}), 200
    order.products.append(product)
    db.session.commit()
    return jsonify(order_schema.dump(order))

@app.delete("/orders/<int:order_id>/remove_product/<int:product_id>")
def remove_product_from_order(order_id, product_id):
    order = Order.query.get_or_404(order_id)
    product = Product.query.get_or_404(product_id)
    if product not in order.products:
        return jsonify({"message": "Product not in order"}), 404
    order.products.remove(product)
    db.session.commit()
    return jsonify({"message": "Product removed", "order": order_schema.dump(order)})

@app.get("/orders/user/<int:user_id>")
def get_orders_for_user(user_id):
    User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user_id).all()
    return jsonify(orders_schema.dump(orders))

@app.get("/orders/<int:order_id>/products")
def get_products_for_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify(products_schema.dump(order.products))

# ------------ ROOT ------------

@app.get("/")
def root():
    return jsonify({"status": "ok", "service": "ecommerce_api"})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", port=5000, debug=True)
