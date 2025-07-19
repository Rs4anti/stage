import random
import string
from bson import ObjectId
from mongodb_handler import atomic_services_collection

# Funzioni helper
def random_string(length=6):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_bool():
    return random.choice([True, False])

def random_float():
    return round(random.uniform(1, 100), 3)

def random_int():
    return random.randint(1, 100)

# Seeder loop
for i in range(30):
    doc = {
        'task_id': f'Activity_{random_string(8)}',
        'atomic_type': random.choice(['collect', 'process&monitor', 'dispatch', 'display']),
        'diagram_id': str(ObjectId()),
        'input_params': [
            {'value': random_string(), 'type': 'string'},
            {'value': str(random_bool()), 'type': 'bool'},
            {'value': str(random_float()), 'type': 'float'},
            {'value': str(random_float()), 'type': 'float'}
        ],
        'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
        'name': f'as_{i}',
        'output_params': [
            {'value': random_string(), 'type': 'string'},
            {'value': str(random_bool()).lower(), 'type': 'bool'},
            {'value': str(random_int()), 'type': 'int'}
        ],
        'owner': random.choice(['paolo', 'maria', 'giulia', 'luca']),
        'url': f'/prova{i}'
    }

    atomic_services_collection.insert_one(doc)

print("✅ Inseriti 30 documenti di test in 'atomic_services'")