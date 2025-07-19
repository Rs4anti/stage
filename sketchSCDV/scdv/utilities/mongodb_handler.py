from pymongo import MongoClient
from bson import ObjectId

client = MongoClient("mongodb://localhost:27017/")
db = client["scdv_db"]

atomic_services_collection = db['atomic_services']
atomic_df = db['atomic_df']
atomic_df_overview = db['atomic_df_overview']
atomic_df_params = db['atomic_df_params']
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
            # Save atomic
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

            # Load back from Mongo
            doc = atomic_services_collection.find_one({'task_id': data['task_id']}, {'_id': 0})
            doc['diagram_id'] = str(doc['diagram_id'])
            #doc.pop('_id', None)

            # Build and persist dataframe
            from utilities.mongodb_dataframe_builder import AtomicServiceDataFrameBuilder
            overview_df, params_df = AtomicServiceDataFrameBuilder.from_document(doc)
            MongoDBHandler.persist_atomic_dataframes(overview_df, params_df, mode='nested')

            return {'status': 'ok', 'created': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500

    @staticmethod
    def persist_atomic_dataframes(overview_df, params_df, mode='nested'):
        """
        Salva i dataframe su MongoDB.

        mode:
        - 'nested': salva overview + params come unico documento con array params
        - 'separate': salva overview e params in due collezioni separate
        """
        overview_records = overview_df.to_dict(orient='records')
        params_records = params_df.to_dict(orient='records')

        if not overview_records:
            print("⚠️ Overview dataframe is empty, skipping persistence.")
            return

        task_id = overview_records[0]['task_id']

        if mode == 'nested':
            doc = {**overview_records[0], 'params': params_records}
            atomic_df.replace_one({'task_id': task_id}, doc, upsert=True)
            print(f"✅ Saved as nested document for task_id: {task_id}")

        elif mode == 'separate':
            atomic_df_overview.replace_one({'task_id': task_id}, overview_records[0], upsert=True)
            if params_records:
                atomic_df_params.delete_many({'task_id': task_id})  # clean old params for this task
                atomic_df_params.insert_many(params_records)
            print(f"✅ Saved in separate collections for task_id: {task_id}")

        else:
            raise ValueError("❌ Unknown mode: choose from 'nested' or 'separate'")

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