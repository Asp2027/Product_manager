
from fastapi.templating import Jinja2Templates
from database import get_db
from fastapi import APIRouter, Form, Depends, status, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User
from passlib.context import CryptContext
from passlib.exc import UnknownHashError, InvalidHashError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/")
def home(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("base.html", {"request": request, "user": user})

@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register_user(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Check if user already exists
    user = db.query(User).filter(User.email == email).first()
    if user:
        return templates.TemplateResponse("register.html", {"request": request, "msg": "Email already registered."})
    
    try:
        # Hash password
        hashed_password = pwd_context.hash(password)
        logger.info(f"Creating user with email: {email}")
        logger.info(f"Hashed password length: {len(hashed_password)}")
        
        # Create new user
        new_user = User(email=email, password=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"User created successfully: {email}")
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        return templates.TemplateResponse("register.html", {"request": request, "msg": "Registration failed. Please try again."})

@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
def login_user(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"Login attempt for non-existent user: {email}")
            return templates.TemplateResponse("login.html", {"request": request, "msg": "Invalid credentials"})
        
        # Debug logging
        logger.info(f"Login attempt for user: {email}")
        logger.info(f"Stored password length: {len(user.password) if user.password else 0}")
        
        # Check if password is None or empty
        if not user.password:
            logger.error(f"User {email} has no password stored")
            return templates.TemplateResponse("login.html", {"request": request, "msg": "Account error. Please contact support."})
        
        # Verify password with proper error handling
        try:
            password_valid = pwd_context.verify(password, user.password)
            if not password_valid:
                logger.warning(f"Invalid password for user: {email}")
                return templates.TemplateResponse("login.html", {"request": request, "msg": "Invalid credentials"})
                
        except UnknownHashError:
            logger.error(f"Unknown hash format for user: {email}. Hash: {user.password[:20]}...")
            return templates.TemplateResponse("login.html", {"request": request, "msg": "Account error. Please contact support."})
            
        except InvalidHashError:
            logger.error(f"Invalid hash format for user: {email}")
            return templates.TemplateResponse("login.html", {"request": request, "msg": "Account error. Please contact support."})
            
        except Exception as hash_error:
            logger.error(f"Unexpected error during password verification for {email}: {hash_error}")
            return templates.TemplateResponse("login.html", {"request": request, "msg": "Login error. Please try again."})
        
        # Successful login
        request.session["user"] = user.email
        logger.info(f"Successful login for user: {email}")
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Unexpected error in login_user: {e}")
        return templates.TemplateResponse("login.html", {"request": request, "msg": "Login error. Please try again."})

@router.get("/logout")
def logout(request: Request):
    user_email = request.session.get("user")
    request.session.clear()
    if user_email:
        logger.info(f"User logged out: {user_email}")
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

# Utility function to check and fix password hashes (for debugging)
@router.get("/debug/check-passwords")
def check_passwords(db: Session = Depends(get_db)):
    """Debug endpoint to check password formats - remove in production"""
    users = db.query(User).all()
    results = []
    
    for user in users:
        password_info = {
            "email": user.email,
            "has_password": bool(user.password),
            "password_length": len(user.password) if user.password else 0,
            "looks_like_bcrypt": user.password.startswith("$2b$") if user.password else False
        }
        results.append(password_info)
    
    return {"users": results}

# Utility function to rehash a user's password (for fixing existing data)
@router.post("/debug/rehash-password")
def rehash_password(email: str = Form(...), new_password: str = Form(...), db: Session = Depends(get_db)):
    """Debug endpoint to rehash a user's password - remove in production"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "User not found"}
    
    try:
        hashed_password = pwd_context.hash(new_password)
        user.password = hashed_password
        db.commit()
        logger.info(f"Password rehashed for user: {email}")
        return {"success": f"Password updated for {email}"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error rehashing password for {email}: {e}")
        return {"error": "Failed to update password"}