from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from extensions import db
from models import User, Account, Transaction
from datetime import datetime, date
import qrcode
import base64
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# ========================
# AUTHENTICATION ROUTES
# ========================
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data.get("full_name") or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Missing required fields"}), 400
    
    if len(data["password"]) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409
    
    user = User(
        full_name=data["full_name"],
        email=data["email"]
    )
    user.set_password(data["password"])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        "message": "User registered successfully",
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login user and return JWT token"""
    data = request.get_json()
    
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
    
    user = User.query.filter_by(email=data["email"]).first()
    
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_user_info():
    """Get current user's info"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat()
    }), 200


# ========================
# ACCOUNT ROUTES
# ========================
account_bp = Blueprint("account", __name__, url_prefix="/api/account")


def generate_upi_id(full_name):
    """Generate UPI ID from user's full name"""
    base = full_name.lower().replace(" ", "")[:20]
    return f"{base}@chalopay"


@account_bp.route("/create", methods=["POST"])
@jwt_required()
def create_account():
    """Create a UPI account for logged-in user"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    existing_account = Account.query.filter_by(user_id=user.id).first()
    if existing_account:
        return jsonify({"error": "User already has a UPI account"}), 400
    
    data = request.get_json()
    mobile = data.get("mobile_number")
    
    if not mobile:
        return jsonify({"error": "Mobile number required"}), 400
    
    if len(mobile) != 10 or not mobile.isdigit():
        return jsonify({"error": "Mobile number must be 10 digits"}), 400
    
    if Account.query.filter_by(mobile_number=mobile).first():
        return jsonify({"error": "Mobile number already registered"}), 409
    
    upi_id = generate_upi_id(user.full_name)
    
    if Account.query.filter_by(upi_id=upi_id).first():
        upi_id = f"{upi_id}{user.id}"
    
    account = Account(
        user_id=user.id,
        mobile_number=mobile,
        upi_id=upi_id,
        balance=10000.0
    )
    
    db.session.add(account)
    db.session.commit()
    
    return jsonify({
        "message": "UPI Account created successfully",
        "upi_id": account.upi_id,
        "mobile_number": account.mobile_number,
        "balance": account.balance,
        "created_at": account.created_at.isoformat()
    }), 201


@account_bp.route("/info", methods=["GET"])
@jwt_required()
def get_account_info():
    """Get user's UPI account info"""
    user_id = get_jwt_identity()
    account = Account.query.filter_by(user_id=int(user_id)).first()
    
    if not account:
        return jsonify({"error": "No UPI account found. Create one first!"}), 404
    
    return jsonify({
        "upi_id": account.upi_id,
        "mobile_number": account.mobile_number,
        "balance": account.balance,
        "created_at": account.created_at.isoformat()
    }), 200


@account_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def get_dashboard():
    """Get dashboard info for logged-in user"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    account = Account.query.filter_by(user_id=user.id).first()
    
    if not account:
        return jsonify({
            "message": "No UPI account yet",
            "user": {
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role
            },
            "account": None,
            "actions": ["create_account"]
        }), 200
    
    return jsonify({
        "message": f"Welcome, {user.full_name}! 💜",
        "user": {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        },
        "account": {
            "upi_id": account.upi_id,
            "mobile_number": account.mobile_number,
            "balance": account.balance,
            "created_at": account.created_at.isoformat()
        },
        "actions": [
            "send_money",
            "view_history",
            "qr_payment",
            "view_profile"
        ]
    }), 200


# ========================
# TRANSACTION ROUTES
# ========================
transaction_bp = Blueprint("transaction", __name__, url_prefix="/api/transaction")


@transaction_bp.route("/send", methods=["POST"])
@jwt_required()
def send_money():
    """Send money from sender to receiver"""
    sender_id = get_jwt_identity()
    sender = User.query.get(int(sender_id))
    
    if not sender:
        return jsonify({"error": "Sender not found"}), 404
    
    sender_account = Account.query.filter_by(user_id=sender.id).first()
    if not sender_account:
        return jsonify({"error": "Create a UPI account first!"}), 400
    
    data = request.get_json()
    receiver_upi = data.get("receiver_upi")
    amount = data.get("amount")
    description = data.get("description", "")
    
    if not receiver_upi or not amount:
        return jsonify({"error": "receiver_upi and amount required"}), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400
    
    if sender_account.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    
    # Check if sender account is frozen
    if sender_account.is_frozen:
        return jsonify({"error": "Your account is frozen. Contact admin."}), 403

    # ===== DAILY LIMIT CHECK =====
    DAILY_LIMIT = 10000.0
    today = date.today()
    
    # Get all transactions sent today
    daily_sent = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.sender_id == sender.id,
        Transaction.status == "success",
        db.func.date(Transaction.created_at) == today
    ).scalar() or 0.0
    
    if daily_sent + amount > DAILY_LIMIT:
        remaining = DAILY_LIMIT - daily_sent
        return jsonify({
            "error": f"Daily limit exceeded! Daily limit is Rs.{DAILY_LIMIT}. You have Rs.{remaining:.2f} remaining today."
        }), 400
    # ===== END DAILY LIMIT CHECK =====
    
    receiver_account = Account.query.filter_by(upi_id=receiver_upi).first()
    if not receiver_account:
        return jsonify({"error": "Receiver UPI ID not found"}), 404
    
    if sender_account.id == receiver_account.id:
        return jsonify({"error": "Cannot send money to yourself"}), 400
    
    # Check if receiver account is frozen
    if receiver_account.is_frozen:
        return jsonify({"error": "Receiver account is frozen"}), 403
    
    try:
        sender_account.balance -= amount
        receiver_account.balance += amount
        
        transaction = Transaction(
            sender_id=sender.id,
            receiver_id=receiver_account.user_id,
            amount=amount,
            status="success",
            description=description
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        # Calculate remaining daily limit
        remaining_limit = DAILY_LIMIT - (daily_sent + amount)
        
        return jsonify({
            "message": "Money sent successfully",
            "transaction_id": transaction.id,
            "sender_upi": sender_account.upi_id,
            "receiver_upi": receiver_account.upi_id,
            "amount": amount,
            "sender_balance": sender_account.balance,
            "receiver_balance": receiver_account.balance,
            "timestamp": transaction.created_at.isoformat(),
            "description": description,
            "daily_limit_remaining": remaining_limit
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Transaction failed: {str(e)}"}), 500

@transaction_bp.route("/history", methods=["GET"])
@jwt_required()
def get_transaction_history():
    """Get all transactions for logged-in user"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    filter_by = request.args.get("filter_by", "all")
    
    if filter_by == "sent":
        transactions = Transaction.query.filter_by(sender_id=user.id)
    elif filter_by == "received":
        transactions = Transaction.query.filter_by(receiver_id=user.id)
    else:
        transactions = Transaction.query.filter(
            (Transaction.sender_id == user.id) | 
            (Transaction.receiver_id == user.id)
        )
    
    transactions = transactions.order_by(Transaction.created_at.desc()).all()
    
    transaction_list = []
    for txn in transactions:
        if txn.sender_id == user.id:
            txn_type = "sent"
            receiver_account = Account.query.filter_by(user_id=txn.receiver_id).first()
            other_party_upi = receiver_account.upi_id if receiver_account else "Unknown"
            other_party_name = txn.receiver.full_name
        else:
            txn_type = "received"
            sender_account = Account.query.filter_by(user_id=txn.sender_id).first()
            other_party_upi = sender_account.upi_id if sender_account else "Unknown"
            other_party_name = txn.sender.full_name
        
        transaction_list.append({
            "transaction_id": txn.id,
            "type": txn_type,
            "amount": txn.amount,
            "other_party_name": other_party_name,
            "other_party_upi": other_party_upi,
            "status": txn.status,
            "description": txn.description,
            "timestamp": txn.created_at.isoformat()
        })
    
    return jsonify({
        "message": f"Found {len(transaction_list)} transactions",
        "total_transactions": len(transaction_list),
        "filter": filter_by,
        "transactions": transaction_list
    }), 200


@transaction_bp.route("/summary", methods=["GET"])
@jwt_required()
def get_transaction_summary():
    """Get transaction summary"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    sent_txns = Transaction.query.filter_by(sender_id=user.id).all()
    received_txns = Transaction.query.filter_by(receiver_id=user.id).all()
    
    total_sent = sum([txn.amount for txn in sent_txns])
    total_received = sum([txn.amount for txn in received_txns])
    
    return jsonify({
        "total_sent": total_sent,
        "total_received": total_received,
        "total_transactions_sent": len(sent_txns),
        "total_transactions_received": len(received_txns),
        "net_balance_change": total_received - total_sent
    }), 200

@transaction_bp.route("/search", methods=["GET"])
@jwt_required()
def search_transactions():
    """
    Search transactions by various filters
    Query params:
    - upi_id: search by other party's UPI ID
    - min_amount: minimum amount
    - max_amount: maximum amount
    - description: search in description
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    """
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get search parameters
    upi_id = request.args.get("upi_id")
    min_amount = request.args.get("min_amount")
    max_amount = request.args.get("max_amount")
    description = request.args.get("description")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    # Base query - all transactions for this user
    query = Transaction.query.filter(
        (Transaction.sender_id == user.id) | 
        (Transaction.receiver_id == user.id)
    )
    
    # Filter by amount range
    if min_amount:
        try:
            query = query.filter(Transaction.amount >= float(min_amount))
        except ValueError:
            return jsonify({"error": "Invalid min_amount"}), 400
    
    if max_amount:
        try:
            query = query.filter(Transaction.amount <= float(max_amount))
        except ValueError:
            return jsonify({"error": "Invalid max_amount"}), 400
    
    # Filter by description (partial match)
    if description:
        query = query.filter(Transaction.description.ilike(f"%{description}%"))
    
    # Filter by date range
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(Transaction.created_at >= start)
        except:
            return jsonify({"error": "Invalid start_date format (use YYYY-MM-DD)"}), 400
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(Transaction.created_at <= end)
        except:
            return jsonify({"error": "Invalid end_date format (use YYYY-MM-DD)"}), 400
    
    # Get all matching transactions
    transactions = query.order_by(Transaction.created_at.desc()).all()
    
    # Format and filter by UPI ID (post-query since it requires joining accounts)
    transaction_list = []
    for txn in transactions:
        if txn.sender_id == user.id:
            txn_type = "sent"
            other_account = Account.query.filter_by(user_id=txn.receiver_id).first()
            other_party_upi = other_account.upi_id if other_account else "Unknown"
            other_party_name = txn.receiver.full_name
        else:
            txn_type = "received"
            other_account = Account.query.filter_by(user_id=txn.sender_id).first()
            other_party_upi = other_account.upi_id if other_account else "Unknown"
            other_party_name = txn.sender.full_name
        
        # Filter by UPI ID if specified
        if upi_id and upi_id.lower() not in other_party_upi.lower():
            continue
        
        transaction_list.append({
            "transaction_id": txn.id,
            "type": txn_type,
            "amount": txn.amount,
            "other_party_name": other_party_name,
            "other_party_upi": other_party_upi,
            "status": txn.status,
            "description": txn.description,
            "timestamp": txn.created_at.isoformat()
        })
    
    return jsonify({
        "message": f"Found {len(transaction_list)} matching transactions",
        "total_results": len(transaction_list),
        "transactions": transaction_list
    }), 200

@transaction_bp.route("/statement", methods=["GET"])
@jwt_required()
def generate_statement():
    """Generate PDF statement of all transactions"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    account = Account.query.filter_by(user_id=user.id).first()
    if not account:
        return jsonify({"error": "No UPI account found"}), 404
    
    # Get all transactions
    transactions = Transaction.query.filter(
        (Transaction.sender_id == user.id) | 
        (Transaction.receiver_id == user.id)
    ).order_by(Transaction.created_at.desc()).all()
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#8B5CF6'),
        spaceAfter=10
    )
    
    # Title
    elements.append(Paragraph("ChaloPay Transaction Statement", title_style))
    elements.append(Spacer(1, 10))
    
    # Account Info
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=5
    )
    elements.append(Paragraph(f"<b>Account Holder:</b> {user.full_name}", info_style))
    elements.append(Paragraph(f"<b>UPI ID:</b> {account.upi_id}", info_style))
    elements.append(Paragraph(f"<b>Current Balance:</b> Rs.{account.balance:.2f}", info_style))
    elements.append(Paragraph(f"<b>Statement Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", info_style))
    elements.append(Spacer(1, 20))
    
    # Transaction Table
    if transactions:
        data = [['Date', 'Type', 'Party', 'Amount', 'Description']]
        
        for txn in transactions:
            if txn.sender_id == user.id:
                txn_type = "Sent"
                other_account = Account.query.filter_by(user_id=txn.receiver_id).first()
                other_party = other_account.upi_id if other_account else "Unknown"
                amount_str = f"-Rs.{txn.amount:.2f}"
            else:
                txn_type = "Received"
                other_account = Account.query.filter_by(user_id=txn.sender_id).first()
                other_party = other_account.upi_id if other_account else "Unknown"
                amount_str = f"+Rs.{txn.amount:.2f}"
            
            date_str = txn.created_at.strftime('%Y-%m-%d %H:%M')
            description = txn.description[:30] if txn.description else "-"
            
            data.append([date_str, txn_type, other_party, amount_str, description])
        
        # Create table
        table = Table(data, colWidths=[1.2*inch, 0.8*inch, 1.5*inch, 1*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B5CF6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F7FF')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E9D5FF')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F7FF')]),
        ]))
        
        elements.append(table)
    else:
        elements.append(Paragraph("No transactions found.", info_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Generate filename
    filename = f"ChaloPay_Statement_{user.full_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

@transaction_bp.route("/qr-code", methods=["GET"])
@jwt_required()
def generate_qr_code():
    """Generate QR code for user's UPI ID"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    account = Account.query.filter_by(user_id=user.id).first()
    if not account:
        return jsonify({"error": "No UPI account found"}), 404
    
    # Create QR code data
    upi_string = f"upi://pay?receiver={account.upi_id}&name={user.full_name}"
    
    try:
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            "message": "QR code generated successfully",
            "upi_id": account.upi_id,
            "upi_string": upi_string,
            "qr_code_base64": f"data:image/png;base64,{img_base64}"
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Failed to generate QR code: {str(e)}"}), 500


@transaction_bp.route("/qr-decode", methods=["POST"])
@jwt_required()
def decode_qr_code():
    """
    Simulate scanning a QR code
    Expects JSON: {"upi_string": "upi://pay?receiver=aditi@chalopay&name=Aditi"}
    """
    data = request.get_json()
    upi_string = data.get("upi_string")
    
    if not upi_string:
        return jsonify({"error": "upi_string required"}), 400
    
    try:
        # Extract UPI ID from the string
        if "receiver=" in upi_string:
            receiver_upi = upi_string.split("receiver=")[1].split("&")[0]
        else:
            return jsonify({"error": "Invalid UPI string format"}), 400
        
        # Find the account
        account = Account.query.filter_by(upi_id=receiver_upi).first()
        if not account:
            return jsonify({"error": "Receiver UPI ID not found"}), 404
        
        return jsonify({
            "message": "QR code decoded successfully",
            "receiver_upi": receiver_upi,
            "receiver_name": account.user.full_name,
            "receiver_mobile": account.mobile_number
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Failed to decode QR code: {str(e)}"}), 500
    
# ========================
# ADMIN ROUTES
# ========================
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def check_admin(user_id):
    """Helper function to check if user is admin"""
    user = User.query.get(int(user_id))
    if not user or user.role != "admin":
        return False
    return True


@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def get_all_users():
    """Admin: View all users"""
    user_id = get_jwt_identity()
    
    if not check_admin(user_id):
        return jsonify({"error": "Admin access required"}), 403
    
    users = User.query.all()
    
    user_list = []
    for user in users:
        account = Account.query.filter_by(user_id=user.id).first()
        user_list.append({
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "has_account": account is not None,
            "upi_id": account.upi_id if account else None,
            "account_frozen": account.is_frozen if account else False,
            "created_at": user.created_at.isoformat()
        })
    
    return jsonify({
        "message": f"Found {len(user_list)} users",
        "total_users": len(user_list),
        "users": user_list
    }), 200


@admin_bp.route("/transactions", methods=["GET"])
@jwt_required()
def get_all_transactions():
    """Admin: View all transactions"""
    user_id = get_jwt_identity()
    
    if not check_admin(user_id):
        return jsonify({"error": "Admin access required"}), 403
    
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    
    transaction_list = []
    for txn in transactions:
        sender_account = Account.query.filter_by(user_id=txn.sender_id).first()
        receiver_account = Account.query.filter_by(user_id=txn.receiver_id).first()
        
        transaction_list.append({
            "transaction_id": txn.id,
            "sender_name": txn.sender.full_name,
            "sender_upi": sender_account.upi_id if sender_account else "Unknown",
            "receiver_name": txn.receiver.full_name,
            "receiver_upi": receiver_account.upi_id if receiver_account else "Unknown",
            "amount": txn.amount,
            "status": txn.status,
            "description": txn.description,
            "timestamp": txn.created_at.isoformat()
        })
    
    return jsonify({
        "message": f"Found {len(transaction_list)} transactions",
        "total_transactions": len(transaction_list),
        "transactions": transaction_list
    }), 200


@admin_bp.route("/accounts", methods=["GET"])
@jwt_required()
def get_all_accounts():
    """Admin: View all accounts"""
    user_id = get_jwt_identity()
    
    if not check_admin(user_id):
        return jsonify({"error": "Admin access required"}), 403
    
    accounts = Account.query.all()
    
    account_list = []
    for account in accounts:
        account_list.append({
            "account_id": account.id,
            "user_id": account.user_id,
            "user_name": account.user.full_name,
            "user_email": account.user.email,
            "upi_id": account.upi_id,
            "mobile_number": account.mobile_number,
            "balance": account.balance,
            "is_frozen": account.is_frozen,
            "created_at": account.created_at.isoformat()
        })
    
    return jsonify({
        "message": f"Found {len(account_list)} accounts",
        "total_accounts": len(account_list),
        "accounts": account_list
    }), 200


@admin_bp.route("/accounts/<int:account_id>/freeze", methods=["POST"])
@jwt_required()
def freeze_account(account_id):
    """Admin: Freeze an account (block all transactions)"""
    user_id = get_jwt_identity()
    
    if not check_admin(user_id):
        return jsonify({"error": "Admin access required"}), 403
    
    account = Account.query.get(account_id)
    
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    if account.is_frozen:
        return jsonify({"error": "Account already frozen"}), 400
    
    account.is_frozen = True
    db.session.commit()
    
    return jsonify({
        "message": f"Account {account.upi_id} frozen successfully",
        "account_id": account.id,
        "upi_id": account.upi_id,
        "is_frozen": account.is_frozen
    }), 200


@admin_bp.route("/accounts/<int:account_id>/unfreeze", methods=["POST"])
@jwt_required()
def unfreeze_account(account_id):
    """Admin: Unfreeze an account"""
    user_id = get_jwt_identity()
    
    if not check_admin(user_id):
        return jsonify({"error": "Admin access required"}), 403
    
    account = Account.query.get(account_id)
    
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    if not account.is_frozen:
        return jsonify({"error": "Account is not frozen"}), 400
    
    account.is_frozen = False
    db.session.commit()
    
    return jsonify({
        "message": f"Account {account.upi_id} unfrozen successfully",
        "account_id": account.id,
        "upi_id": account.upi_id,
        "is_frozen": account.is_frozen
    }), 200
