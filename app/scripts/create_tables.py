from app import models
from app.database import engine

if __name__ == "__main__":
    models.Base.metadata.create_all(bind=engine)
    print("Tables created.")
