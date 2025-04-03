from pymongo import MongoClient
from django.conf import settings

MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_COLLECTION = "prorva_py_mongo"

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_COLLECTION]
