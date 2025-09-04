from .mongodb_handler import rbac_collection

"""
{'diagram_id': '68b7f887ad90d004364a52ee', 
'task_id': 'Activity_1u1y293', 
'name': 'Send Data for Sales Order', 
'atomic_type': 'dispatch', 
'input_params': ['100'], 
'output_params': ['100'], 
'method': 'POST', 
'url': '/send_data_order', 
'owner': 'Customer'}
"""

class rbac:
    @staticmethod
    def atomic_policy(atomic_data):

        service_type = 'atomic'
        atomic_type = atomic_data['atomic_type']
        task_id = atomic_data['task_id']
        components = [task_id]
        owner = atomic_data['owner']

        actors = [owner]

        #Access Control Matrix
        acm: dict[str, str] = {}
        for actor in actors:
            acm[actor] = {}
            for comp in components:
                acm[actor][comp] = "none"

        #owner può invocare il proprio atomic
        acm[owner][task_id] = 'invoke'

        #costruzione policy
        policy = {
            "task_id" : task_id,
            "service_type" : service_type,
            "atomic_type" : atomic_type,
            "owner" : owner,
            "permissions": 
            [
                {"actor": actor , "permission": perm}
                for actor, cols in acm.items()
                for comp,perm in cols.items()
            ]
        }

        try:
            result = rbac_collection.update_one(
                {'task_id': task_id},
                {'$set': policy},
                upsert=True
            )
            created = result.upserted_id is not None
            
            return {'status': 'ok', 'created policy': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500