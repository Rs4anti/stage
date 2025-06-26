from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["scdv_db"]

atomic_services_collection = db['atomic_services']
cpps_collection = db['cpps']
cppn_collection = db['cppn']