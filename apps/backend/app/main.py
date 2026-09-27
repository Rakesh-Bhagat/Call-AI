from fastapi import FastAPI
from app.api import browser
from app.api import twillio


app = FastAPI()
app.include_router(browser.router)
app.include_router(twillio.router)

@app.get("/health")
def health():
    return {"status": "ok"}