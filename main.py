from fastapi import FastAPI
from database import Base, engine 
from routers import auth,jobs
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Portal API")

app.include_router(auth.router)
app.include_router(jobs.router)

@app.get("/")
def home():
    return {"message": "Welcome to the Job Portal API"}
