from .mongodb_handler import rbac_collection, atomic_services_collection, cpps_collection

class rbac:
    @staticmethod
    def atomic_policy(atomic_data):
        diagram_id = atomic_data['diagram_id']
        atomic_name = atomic_data['name']
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
            'diagram_id': diagram_id,
            'service_name' : atomic_name,
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

    @staticmethod
    def cpps_policy_from_import(cpps_data_import, components):

        atomic_ids = []
        cpps_ids = []
        for c in components:
            if c['type'].lower() == 'atomic':
                atomic_ids.append(c['id'])
            elif c['type'].lower() == 'cpps':
                cpps_ids.append(c['id'])
        
        rbac.cpps_policy(cpps_data_import, atomic_ids, cpps_ids)


    @staticmethod
    def cpps_policy(cpps_data, atomic_ids, cpps_ids):
        cpps_name = cpps_data['name']
        diagram_id = cpps_data['diagram_id']
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
            'diagram_id' : diagram_id,
            'service_name' : cpps_name,
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
                {'cpps_id' : group_id},
                {'$set': policy},
                upsert=True
            )
            created = result.upserted_id is not None
            
            return {'status': 'ok', 'created policy': created}, 200

        except Exception as e:
            return {'error': str(e)}, 500
    
    
    @staticmethod
    def cppn_policy(cppn_data, components_cppn):
        service_name = cppn_data['name']
        diagram_id = cppn_data['diagram_id']
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
            'service_name' : service_name,
            'diagram_id' : diagram_id,
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

    @staticmethod
    def find_atomic_owner(task_id):
        atomic = atomic_services_collection.find_one({'task_id' : task_id })
        return atomic['owner']
    
    @staticmethod
    def find_cpps_owner(group_id):
        cpps = cpps_collection.find_one({'group_id' : group_id })
        return cpps['owner']