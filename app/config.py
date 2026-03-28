"""
Application configuration module isolating environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:  # pylint: disable=too-few-public-methods
    """Base configuration for Flask app."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    # GCP variables
    GCP_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT', 'fourth-arena-491605-j1')
    BUCKET_NAME = os.getenv('BUCKET_NAME', f"staging.{GCP_PROJECT}.appspot.com")
    TOPIC_NAME = os.getenv('TOPIC_NAME', f"projects/{GCP_PROJECT}/topics/disaster-signals-feed")
    FIRESTORE_COLLECTION = os.getenv('FIRESTORE_COLLECTION', 'triage_incidents')
    # Vertex AI
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

class ProductionConfig(Config):  # pylint: disable=too-few-public-methods
    """Production configuration with strict security and logging settings."""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):  # pylint: disable=too-few-public-methods
    """Testing configuration with debug and loose security for simulation."""
    DEBUG = True
    TESTING = True
    SESSION_COOKIE_SECURE = False
