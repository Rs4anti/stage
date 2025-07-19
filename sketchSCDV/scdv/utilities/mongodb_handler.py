from pymongo import MongoClient
from bson import ObjectId

client = MongoClient("mongodb://localhost:27017/")
db = client["scdv_db"]

atomic_services_collection = db['atomic_services']
cpps_collection = db['cpps']
cppn_collection = db['cppn']
bpmn_collection = db['bpmn']
openapi_collection = db['openapi']

class MongoDBHandler:

    @staticmethod
    def save_atomic(data):
        required_fields = ['diagram_id', 'task_id', 'name', 'atomic_type', 'input_params', 'output_params', 'method', 'url', 'owner']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return {'error': f'Missing fields: {", ".join(missing)}'}, 400

        try:
            diagram_id = ObjectId(data['diagram_id'])
        except Exception:
            return {'error': 'Invalid diagram ID'}, 400

        diagram = bpmn_collection.find_one({'_id': diagram_id})
        if not diagram:
            return {'error': 'Diagram not found'}, 404

        try:
            result = atomic_services_collection.update_one(
                {'task_id': data['task_id']},
                {
                    '$set': {
                        'diagram_id': str(diagram_id),
                        'name': data['name'],
                        'atomic_type': data['atomic_type'],
                        'input_params': data['input_params'],
                        'output_params': data['output_params'],
                        'method': data['method'],
                        'url': data['url'],
                        'owner': data['owner']
                    }
                },
                upsert=True
            )
            created = result.upserted_id is not None
            return {'status': 'ok', 'created': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500