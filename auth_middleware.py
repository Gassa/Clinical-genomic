import os, jwt
from functools import wraps
from flask import request, jsonify, session

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

def get_current_user():
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = session.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception:
        return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json:
                return jsonify({"error": "Non authentifié", "redirect": "/login"}), 401
            from flask import redirect
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

def get_user_id():
    user = get_current_user()
    return user.get("sub") if user else None

def get_user_email():
    user = get_current_user()
    return user.get("email") if user else None
