from app.database import engine
from app import models

if __name__ == "__main__":
    models.Base.metadata.create_all(bind=engine)
    print("Tables created.")