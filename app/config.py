from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database configuration variables
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    
    # JWT configuration variables
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Configuration for reading the .env file 
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Property to construct the database URL from the individual components
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

# Instantiate the class to use this variable 'settings' in the entire project
settings = Settings()