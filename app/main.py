from fastapi import FastAPI, status

from app.routes import access, auth, documents, projects

app = FastAPI(title="Project Management API", version="1.0.0")


@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {"message": "API is running successfully"}


app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(access.router)

