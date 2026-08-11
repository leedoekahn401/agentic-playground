import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine the absolute path to the .env file at the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")
    
class Settings(BaseSettings):
    deepseek_api_key: str
    secret: str
    
    # It can also handle automatic type conversions and default values!
    # If .env has MAX_RETRIES=5, it automatically converts it to an integer.
    max_retries: int = 3  
    
    # Tells Pydantic to look for a .env file
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_file_encoding="utf-8")

# Instantiate it once
config = Settings()
