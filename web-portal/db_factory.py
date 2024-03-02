# db_factory.py
from pymongo import MongoClient

# Initialize the MongoDB client and select your database here
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["user_db"]

config_collection = db["config"]
user_collection = db["users"]
experiment_collection = db["experiments"]
