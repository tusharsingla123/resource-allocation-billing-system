"""Authentication routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import db, bcrypt
from app.models import User, Admin
from app.utils.decorators import nocache

bp = Blueprint('auth', __name__)

@bp.route('/')
def home():
    return render_template('login.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('vessels.home_page'))

    if request.method == 'GET':
        return render_template('login.html')

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "No JSON received"}), 400

    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"success": False, "message": "Missing email or password"}), 400

    # Check Admin first
    admin = Admin.query.filter_by(username=email).first()
    if admin and check_password_hash(admin.password_hash, password):
        login_user(admin)
        return jsonify({"success": True, "redirect": url_for("auth.admin_dashboard")}), 200

    # Check normal user
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    if not user.approved:
        return jsonify({"success": False, "message": "Account pending approval"}), 403
    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"success": False, "message": "Incorrect password"}), 401

    login_user(user)
    return jsonify({"success": True, "redirect": url_for("vessels.home_page")}), 200


@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard - only accessible to admin users"""
    if not isinstance(current_user, Admin):
        abort(403, description="Unauthorized: Admins only")
    return render_template('admin.html')


@bp.route("/admin/get_users")
@login_required
def get_users():
    """Get all users - admin only"""
    if not isinstance(current_user, Admin):
        return jsonify({"error": "Unauthorized: Admins only"}), 403

    users = User.query.all()
    user_list = [
        {
            "id": u.id,
            "email": u.email,
            "approved": bool(u.approved)
        }
        for u in users
    ]
    return jsonify(user_list)


@bp.route("/admin/toggle_approval/<int:user_id>", methods=["POST"])
@login_required
def toggle_approval(user_id):
    """Toggle user approval status - admin only"""
    if not isinstance(current_user, Admin):
        return jsonify({"error": "Unauthorized: Admins only"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.approved = not user.approved
    db.session.commit()

    return jsonify({"success": True, "approved": user.approved})


@bp.route('/session_check')
def session_check():
    """Check if user session is active"""
    return jsonify({"authenticated": current_user.is_authenticated})


@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "No data"}), 400

    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered"}), 400

    # Hash password
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    # Create user with approved = False
    user = User(
        email=email,
        password=hashed_pw,
        approved=False       
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Registration successful! Wait for Admin Approval to login."
    }), 200


@bp.route('/logout', methods=['GET', 'POST'])
@nocache
def logout():
    """Logout user"""
    logout_user()
    session.clear()
    resp = redirect(url_for('auth.login'))
    resp.headers['Cache-Control'] = 'no-store'
    return resp
