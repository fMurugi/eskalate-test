from fastapi import FastAPI
from database import Base, engine 
from routers import auth,jobs
import uvicorn
import models
import os
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Portal API")

app.include_router(auth.router)
app.include_router(jobs.router)

@app.get("/")
def home():
    return {"message": "Welcome to the Job Portal API"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)