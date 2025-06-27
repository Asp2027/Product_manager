# routers/products.py

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Product
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])
templates = Jinja2Templates(directory="templates")


def get_current_user(request: Request):
    """Helper function to get current user from session"""
    return request.session.get("user")


def require_auth(request: Request):
    """Helper function to require authentication"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


@router.get("/")
def list_products(request: Request, db: Session = Depends(get_db)):
    """Display all products"""
    try:
        user = get_current_user(request)
        products = db.query(Product).all()
        logger.info(f"Retrieved {len(products)} products")
        
        return templates.TemplateResponse(
            "products_list.html", 
            {"request": request, "products": products, "user": user}
        )
    except Exception as e:
        logger.error(f"Error retrieving products: {e}")
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "error": "Failed to load products"}
        )


@router.get("/create_product")
def create_product_form(request: Request):
    """Show create product form - require authentication"""
    user = require_auth(request)
    return templates.TemplateResponse(
        "create_product.html",
        {"request": request, "user": user}
    )


@router.post("/create_product")
def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    stock: int = Form(default=0),
    db: Session = Depends(get_db)
):
    """Create a new product - require authentication"""
    user = require_auth(request)
    
    try:
        # Validate input
        if price < 0:
            return templates.TemplateResponse(
                "create_product.html",
                {"request": request, "user": user, "error": "Price must be positive"}
            )
        
        if stock < 0:
            return templates.TemplateResponse(
                "create_product.html",
                {"request": request, "user": user, "error": "Stock must be non-negative"}
            )
        
        # Create product
        new_product = Product(
            name=name.strip(),
            description=description.strip(),
            price=price,
            stock=stock
        )
        
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        
        logger.info(f"Product created: {new_product.name} by user {user}")
        return RedirectResponse("/products", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        db.rollback()
        return templates.TemplateResponse(
            "create.html",
            {"request": request, "user": user, "error": "Failed to create product"}
        )


@router.get("/{product_id}")
def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    """Display single product details"""
    try:
        user = get_current_user(request)
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return templates.TemplateResponse(
            "product_list.html",
            {"request": request, "product": product, "user": user}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product {product_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/edit/{product_id}")
def edit_product_form(product_id: int, request: Request, db: Session = Depends(get_db)):
    """Show edit product form - require authentication"""
    user = require_auth(request)
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return templates.TemplateResponse(
        "edit_product.html",
        {"request": request, "product": product, "user": user}
    )


@router.post("/edit/{product_id}")
def update_product(
    product_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    stock: int = Form(default=0),
    db: Session = Depends(get_db)
):
    """Update a product - require authentication"""
    user = require_auth(request)
    
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Validate input
        if price < 0:
            return templates.TemplateResponse(
                "edit_product.html",
                {"request": request, "product": product, "user": user, "error": "Price must be positive"}
            )
        
        # Update product
        product.name = name.strip()
        product.description = description.strip()
        product.price = price
        product.stock = stock
        
        db.commit()
        
        logger.info(f"Product updated: {product.name} by user {user}")
        return RedirectResponse(f"/products/{product_id}", status_code=status.HTTP_303_SEE_OTHER)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/delete/{product_id}")
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a product - require authentication"""
    user = require_auth(request)
    
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product_name = product.name
        db.delete(product)
        db.commit()
        
        logger.info(f"Product deleted: {product_name} by user {user}")
        return RedirectResponse("/products", status_code=status.HTTP_303_SEE_OTHER)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


# Search functionality
@router.get("/search")
def search_products(request: Request, q: str = "", db: Session = Depends(get_db)):
    """Search products by name or description"""
    user = get_current_user(request)
    
    if q.strip():
        products = db.query(Product).filter(
            Product.name.contains(q) | Product.description.contains(q)
        ).all()
    else:
        products = db.query(Product).all()
    
    return templates.TemplateResponse(
        "products_list.html",
        {"request": request, "products": products, "user": user, "search_query": q}
    )