# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from models import Base
from database import engine
from routers import products

app = FastAPI()

# Static & DB
app.mount("/static", StaticFiles(directory="static"), name="static")  # Uncomment this!
Base.metadata.create_all(bind=engine)

# Include the router
app.include_router(products.router)

# Add a basic health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Add favicon endpoint to avoid 404 errors
@app.get("/favicon.ico")
def favicon():
    return {"message": "No favicon"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)