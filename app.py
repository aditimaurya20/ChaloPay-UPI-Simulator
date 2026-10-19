from flask import Flask, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, JWT_SECRET_KEY
from extensions import db
from models import User, Account, Transaction

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY

db.init_app(app)
jwt = JWTManager(app)

from routes import auth_bp, account_bp, transaction_bp, admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(account_bp)
app.register_blueprint(transaction_bp)
app.register_blueprint(admin_bp)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/create-account")
def create_account():
    return render_template("create_account.html")


@app.route("/send-money")
def send_money():
    return render_template("send_money.html")


@app.route("/transaction-history")
def transaction_history():
    return render_template("transaction_history.html")


@app.route("/qr-code")
def qr_code_page():
    return render_template("qr_code.html")


@app.route("/admin")
def admin():
    return render_template("admin_panel.html")

def create_default_admin():
    """Create default admin user"""
    admin = User.query.filter_by(email="admin@chalopay.com").first()
    if not admin:
        admin = User(
            full_name="Admin User",
            email="admin@chalopay.com",
            role="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin created: admin@chalopay.com / admin123")

with app.app_context():
    db.create_all()
    create_default_admin()

if __name__ == "__main__":
    app.run(debug=True)