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

        def detect_type(value):
            # Se già non è stringa, usa direttamente type()
            if isinstance(value, bool):
                return 'bool'
            elif isinstance(value, int):
                return 'int'
            elif isinstance(value, float):
                return 'float'

            # Se è stringa, prova a convertirlo
            if isinstance(value, str):
                val = value.strip()
                if val.lower() in ['true', 'false']:
                    return 'bool'
                try:
                    int(val)
                    return 'int'
                except ValueError:
                    pass
                try:
                    float(val)
                    return 'float'
                except ValueError:
                    pass
                return 'string'
            return 'unknown'


        def process_params(params):
            processed = []
            for item in params:
                processed.append({
                    'value': item,
                    'type': detect_type(item)
                })
            return processed

        input_processed = process_params(data['input_params'])
        output_processed = process_params(data['output_params'])

        try:
            result = atomic_services_collection.update_one(
                {'task_id': data['task_id']},
                {
                    '$set': {
                        'diagram_id': str(diagram_id),
                        'name': data['name'],
                        'atomic_type': data['atomic_type'],
                        'input_params': input_processed,
                        'output_params': output_processed,
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
        
    
    @staticmethod
    def save_cppn(data):
        required_fields = [
            'diagram_id',
            'group_id',
            'name',
            'description',
            'workflow_type',
            'members',
            'actors',
            'gdpr_map'
        ]

        missing = [f for f in required_fields if f not in data]
        if missing:
            return {'error': f'Missing fields: {", ".join(missing)}'}, 400

        if not isinstance(data['actors'], list):
            return {'error': 'Field "actors" must be a list'}, 400

        if not isinstance(data['gdpr_map'], dict):
            return {'error': 'Field "gdpr_map" must be a JSON object'}, 400

        try:
            diagram_id = ObjectId(data['diagram_id'])
        except Exception:
            return {'error': 'Invalid diagram ID'}, 400

        diagram = bpmn_collection.find_one({'_id': diagram_id})
        if not diagram:
            return {'error': 'Diagram not found'}, 404

        try:
            doc = {
                "group_type": "CPPN",
                'diagram_id': str(diagram_id),
                'group_id': data['group_id'],
                'name': data['name'],
                'description': data['description'],
                'workflow_type': data['workflow_type'],
                'actors': data['actors'],
                'gdpr_map': data['gdpr_map'],
            }

            # Unisco atomic_services + nested_cpps in components
            doc['components'] = data.get('components', data['members'] + data.get('nested_cpps', []))

            result = cppn_collection.update_one(
                {'group_id': data['group_id']},
                {'$set': doc},
                upsert=True
            )

            created = result.upserted_id is not None
            return {'status': 'ok', 'created': created}, 200

        except Exception as e:
            return {'error': str(e)}, 

    @staticmethod
    def save_cpps(data):
        required_fields = [
            'diagram_id',
            'group_id',
            'name',
            'description',
            'workflow_type',
            'members',
            'actor',
            'endpoints'
        ]

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
            doc = {
                "group_type": "CPPS",
                "diagram_id": str(diagram_id),
                "group_id": data['group_id'],
                "name": data['name'],
                "description": data['description'],
                "workflow_type": data['workflow_type'],
                "actor": data['actor'],
                "endpoints": data['endpoints'],
                "components": data['members'] + data.get('nested_cpps', [])
            }

            result = cpps_collection.update_one(
                {'group_id': data['group_id']},
                {'$set': doc},
                upsert=True
            )

            created = result.upserted_id is not None
            return {'status': 'ok', 'created': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500