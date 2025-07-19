import random
import string
from bson import ObjectId
from mongodb_handler import atomic_services_collection

# Funzioni helper
def random_string(length=6):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_bool():
    return str(random.choice([True, False]))

def random_float():
    return str(round(random.uniform(1, 100), 2))

def random_int():
    return str(random.randint(1, 100))

# Seeder loop
for i in range(30):
    doc = {
        'task_id': f'Activity_{random_string(8)}',
        'atomic_type': random.choice(['collect', 'process&monitor', 'dispatch', 'display']),
        'diagram_id': str(ObjectId()),
        'input': [
            random_string(),
            random_bool(),
            random_int(),
            random_float()
        ],
        'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
        'name': f'as_{i}',
        'output': [
            random_string(),
            random_bool(),
            random_int()
        ],
        'owner': random.choice(['paolo', 'maria', 'giulia', 'luca']),
        'url': f'/url{i}'
    }

    atomic_services_collection.insert_one(doc)

print("✅ Inseriti 30 documenti di test in 'atomic_services'")
