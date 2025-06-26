from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Server is working!"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)