from datetime import datetime
from extensions import db
from werkzeug.security import check_password_hash, generate_password_hash


class User(db.Model):
    """User Model"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password during login"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class Transaction(db.Model):
    """Transaction Model - records all payments"""
    __tablename__ = "transactions"
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="success")
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_transactions")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="received_transactions")
    
    def __repr__(self):
        return f'<Transaction {self.id}: ₹{self.amount}>'
    
class Account(db.Model):
    """Virtual UPI Account Model"""
    __tablename__ = "accounts"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mobile_number = db.Column(db.String(10), unique=True, nullable=False)
    upi_id = db.Column(db.String(50), unique=True, nullable=False)
    balance = db.Column(db.Float, default=10000.0)
    is_frozen = db.Column(db.Boolean, default=False)  # ADD THIS
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="accounts")
    
    def __repr__(self):
        return f'<Account {self.upi_id}>'