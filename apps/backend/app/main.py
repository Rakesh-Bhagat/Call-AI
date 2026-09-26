from fastapi import FastAPI
from app.api import browser


app = FastAPI()
app.include_router(browser.router)

@app.get("/health")
def health():
    return {"status": "ok"}