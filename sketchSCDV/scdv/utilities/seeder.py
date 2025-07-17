import random
import string
from bson import ObjectId
import pandas as pd

class AtomicServiceSeeder:
    ALLOWED_TYPES = ['String', 'Int', 'Float', 'Bool']

    def __init__(self, mongo_collection, num_services=10):
        """
        :param mongo_collection: pymongo collection (es. db.atomic_services_collection)
        :param num_services: numero di servizi da generare
        """
        self.collection = mongo_collection
        self.num_services = num_services

    def random_string(self, length=8):
        return ''.join(random.choices(string.ascii_letters, k=length))

    def random_type(self):
        return random.choice(self.ALLOWED_TYPES)

    def random_value_for_type(self, type_):
        if type_ == 'Int':
            return str(random.randint(0, 100))
        elif type_ == 'Float':
            return str(round(random.uniform(0, 100), 2))
        elif type_ == 'Bool':
            return random.choice(['True', 'False'])
        elif type_ == 'String':
            return self.random_string(5)
        else:
            return 'Unknown'

    def random_params(self, count=3):
        params = []
        for _ in range(count):
            type_ = self.random_type()
            value = self.random_value_for_type(type_)
            params.append({'name': value, 'type': type_})
        return params

    def generate_service(self):
        diagram_id = ObjectId()
        task_id = self.random_string(10)
        name = self.random_string(12)
        atomic_type = random.choice(['collect', 'process', 'dispatch', 'display'])
        method = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
        url = f"/{self.random_string(6)}"
        owner = self.random_string(10)
        input_params = self.random_params()
        output_params = self.random_params()

        df_main = pd.DataFrame([{
            'diagram_id': str(diagram_id),
            'task_id': task_id,
            'name': name,
            'atomic_type': atomic_type,
            'method': method,
            'url': url,
            'owner': owner
        }])

        df_input = pd.DataFrame(input_params)
        df_output = pd.DataFrame(output_params)

        serialized = {
            'main': df_main.to_dict(orient='records'),
            'input_params': df_input.to_dict(orient='records'),
            'output_params': df_output.to_dict(orient='records')
        }

        doc = {
            'diagram_id': str(diagram_id),
            'task_id': task_id,
            'name': name,
            'atomic_type': atomic_type,
            'method': method,
            'url': url,
            'owner': owner,
            'dataframe_serialized': serialized
        }
        return doc

    def seed(self):
        services = [self.generate_service() for _ in range(self.num_services)]
        result = self.collection.insert_many(services)
        print(f"✅ Inseriti {len(result.inserted_ids)} atomic services in MongoDB.")