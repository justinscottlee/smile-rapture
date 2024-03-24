from pymongo import MongoClient

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["user_db"]

config_collection = db["config"]
user_collection = db["users"]
experiment_collection = db["experiments"]

# To delete all data: for testing!
# config_collection.delete_many({})
# user_collection.delete_many({})
# experiment_collection.delete_many({})
#
# for e in experiment_collection.find({}):
#     print(e)
