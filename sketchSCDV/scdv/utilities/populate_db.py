from pymongo import MongoClient
from utilities.seeder import AtomicServiceSeeder

client = MongoClient('mongodb://localhost:27017/')
db = client['scdv_db']
collection = db['atomic_services']

seeder = AtomicServiceSeeder(collection, num_services=20)
seeder.seed()