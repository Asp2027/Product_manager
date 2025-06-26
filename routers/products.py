# routers/products.py

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Product

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
def read_products(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return templates.TemplateResponse("index.html", {"request": request, "products": products})

@router.get("/create")
def create_form(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@router.post("/create")
def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    db: Session = Depends(get_db)
):
    new_product = Product(name=name, description=description, price=price)
    db.add(new_product)
    db.commit()
    return RedirectResponse("/", status_code=303)

@router.get("/delete/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse("/", status_code=303)
