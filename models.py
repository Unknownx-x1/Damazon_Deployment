from flask_login import UserMixin
from extensions import db


# -------------------------
# USER TABLE
# -------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)


# -------------------------
# PRODUCT TABLE (WITH IMAGE)
# -------------------------
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

    image = db.Column(db.String(200))  # NEW FIELD

    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    seller = db.relationship('User', backref='products')


# -------------------------
# ORDER TABLE
# -------------------------
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Pending")

    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))

    buyer = db.relationship('User', backref='orders')
    product = db.relationship('Product', backref='orders')


# -------------------------
# CART TABLE
# -------------------------
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    quantity = db.Column(db.Integer, nullable=False)

    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))

    buyer = db.relationship('User', backref='cart_items')
    product = db.relationship('Product')