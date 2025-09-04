from .mongodb_handler import rbac_collection, atomic_services_collection, cpps_collection

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
                {'atomic_id': task_id},
                {'$set': policy},
                upsert=True
            )
            created = result.upserted_id is not None
            
            return {'status': 'ok', 'created policy': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500

    """{'diagram_id': '68b7f887ad90d004364a52ee', 
    'group_id': 'Group_1hve9wj',
    'name': 'quality check cpps', 
    'description': 'quality check modificato', 
    'workflow_type': 'sequence',
    'components': [{'id': 'Activity_1idq175', 'type': 'Atomic'},
        {'id': 'Activity_1p3burn', 'type': 'Atomic'},
        {'id': 'Activity_0t9nnj9', 'type': 'Atomic'}, 
        {'id': 'Activity_07u2eot', 'type': 'Atomic'},
            {'id': 'Gateway_0ec3hv5', 'type': 'ParallelGateway', 'targets': ['Activity_1p3burn', 'Activity_1idq175']}, 
            {'id': 'Gateway_0yh6vnf', 'type': 'ParallelGateway', 'targets': ['Activity_0t9nnj9']}], 
            'workflow': {'Gateway_0ec3hv5': ['Activity_1p3burn', 'Activity_1idq175'], 
                'Activity_1p3burn': ['Gateway_0yh6vnf'], 'Activity_1idq175': ['Gateway_0yh6vnf'], 
                'Gateway_0yh6vnf': ['Activity_0t9nnj9'], 'Activity_0t9nnj9': ['Activity_07u2eot']}, 
            
            'group_type': 'CPPS', 
            'owner': 'Production Leader', 
            'endpoints': []}
    """ 
    @staticmethod
    def cpps_policy(cpps_data, atomic_ids, cpps_ids):
        service_type = 'cpps'
        group_id = cpps_data['group_id']
        components = atomic_ids
        owner = cpps_data['owner']

        if cpps_ids:
            components = components + cpps_ids
        
        acm: dict[str, str] = {}
        acm[owner] = {}
        for comp in components:
            acm[owner][comp] = "invoke"
        
        #costruzione policy
        policy = {
            "service_type" : service_type,
            "owner" : owner,
            "permissions": 
            [
                {"actor": actor , "service" : comp , "permission": perm}
                for actor, cols in acm.items()
                for comp,perm in cols.items()
            ]
        }

        try:
            result = rbac_collection.update_one(
                {"cpps_id" : group_id},
                {'$set': policy},
                upsert=True
            )
            created = result.upserted_id is not None
            
            return {'status': 'ok', 'created policy': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500

    def cppn_policy(cppn_data, components_cppn):
        service_type = 'cppn'
        group_id = cppn_data['group_id']
        
        actors = set()
        components = []
        comp_owner = {}

        for c in components_cppn:
            if c['type'].lower() == 'atomic':
                cid = c['id']
                components.append(cid)
                owner = rbac.find_atomic_owner(cid)

            elif c['type'].lower() == 'cpps':
                cid = c['id']
                components.append(cid)
                owner = rbac.find_cpps_owner(cid)
            if owner:
                actors.add(owner)
                comp_owner[cid] = owner

        # --- ACM: inizializza tutto a 'none'
        # acm è una matrice: righe=actors, colonne=components
        acm = {actor: {cid: "none" for cid in components} for actor in sorted(actors)}


        #autorizzo l'owner sul proprio componente
        for c, owner in comp_owner.items():
            acm[owner][c] = "invoke"

        policy = {
            "service_type" : service_type,
            "actors" : list(actors),
            "permissions": [
            {"actor": actor, "service": comp, "permission": perm}
            for actor, cols in acm.items()
            for comp, perm in cols.items()
            ]
        }

        try:
            result = rbac_collection.update_one(
                {"cppn_id" : group_id},
                {'$set': policy},
                upsert=True
            )
            created = result.upserted_id is not None
            
            return {'status': 'ok', 'created policy': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500



        
        """
        if cpps_ids:
            components = components + cpps_ids
        
        acm: dict[str, str] = {}
        acm[owner] = {}
        for comp in components:
            acm[owner][comp] = "invoke"
        
        #costruzione policy
        policy = {
            "service_type" : service_type,
            "owner" : owner,
            "permissions": 
            [
                {"actor": actor , "service" : comp , "permission": perm}
                for actor, cols in acm.items()
                for comp,perm in cols.items()
            ]
        }

        try:
            result = rbac_collection.update_one(
                {"activity_id" : group_id},
                {'$set': policy},
                upsert=True
            )
            created = result.upserted_id is not None
            
            return {'status': 'ok', 'created policy': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500
        """


    @staticmethod
    def find_atomic_owner(task_id):
        atomic = atomic_services_collection.find_one({'task_id' : task_id })
        return atomic['owner']
    
    @staticmethod
    def find_cpps_owner(group_id):
        cpps = cpps_collection.find_one({'group_id' : group_id })
        return cpps['owner']