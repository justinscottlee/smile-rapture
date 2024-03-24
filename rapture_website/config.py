import os

from app.models import NodeType

basedir = os.path.abspath(os.path.dirname(__file__))
# load_dotenv(os.path.join(basedir, '.env'))


class Config:
    FAKE_MODE = True
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads/")
    SECRET_KEY = os.urandom(24).hex()
    REGISTRY_URI = "130.191.162.166:5000"

    VALID_IMAGES = ["python:latest", "python:3.10-bullseye", "python:3.12-bookworm", "python:3.11-bookworm"]
    NODE_TYPES = [node_type.name for node_type in NodeType]

    ADMINS = ['admin@admin.com']
    LANGUAGES = ['en', 'es']
    POSTS_PER_PAGE = 25
