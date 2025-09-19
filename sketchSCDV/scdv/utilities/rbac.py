from .mongodb_handler import rbac_collection, atomic_services_collection, cpps_collection
from datetime import datetime

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
        """
        Costruisce/aggiorna la policy CPPN salvando SOLO le tuple 'invoke'.
        NIENTE 'none': la negazione è implicita (assenza di tupla).

        cppn_data: {
            'name': ...,
            'diagram_id': ...,
            'group_id': ...,
            ...
        }
        components_cppn: iterable di dict con chiavi:
            - type: 'atomic' | 'cpps'
            - id:   service id (es. Activity_xxx o Group_xxx)
        """
        service_name = cppn_data['name']
        diagram_id   = cppn_data['diagram_id']
        group_id     = cppn_data['group_id']          # cppn_id
        service_type = 'cppn'

        actors      = set()
        components  = []
        comp_owner  = {}  # service_id -> owner

        for c in components_cppn:
            ctype = (c.get('type') or '').lower()
            cid   = c.get('id')
            if not cid:
                continue
            
            if ctype == 'atomic' or ctype == 'cpps':
                components.append(cid)

            owner = None
            if ctype == 'atomic':
                owner = rbac.find_atomic_owner(cid)
            elif ctype == 'cpps':
                owner = rbac.find_cpps_owner(cid)

            if owner:
                actors.add(owner)
                comp_owner[cid] = owner

        # Costruisci SOLO le tuple 'invoke' (owner -> proprio componente)
        # Niente ACM con 'none'
        invoke_pairs = {(own, sid) for sid, own in comp_owner.items() if own}
        permissions = [
            {"actor": a, "service": s, "permission": "invoke"}
            for (a, s) in sorted(invoke_pairs)
        ]

        policy = {
            "cppn_id"      : group_id,
            "service_name" : service_name,
            "diagram_id"   : diagram_id,
            "service_type" : service_type,
            "actors"       : sorted(actors),     # opzionale, elenco attori coinvolti
            "members"      : sorted(set(components)),  # opzionale, elenco servizi membri del CPPN
            "permissions"  : permissions,        # SOLO 'invoke'
            "updated_at"   : datetime.utcnow(),
        }

        try:
            result = rbac_collection.update_one(
                {"diagram_id": diagram_id, "service_type": "cppn", "cppn_id": group_id},
                {"$set": policy},
                upsert=True
            )
            created = result.upserted_id is not None
            return {"status": "ok", "created_policy": created, "invoke_count": len(permissions)}, 200

        except Exception as e:
            return {"error": str(e)}, 500

    @staticmethod
    def find_atomic_owner(task_id):
        atomic = atomic_services_collection.find_one({'task_id' : task_id })
        return atomic['owner']
    
    @staticmethod
    def find_cpps_owner(group_id):
        cpps = cpps_collection.find_one({'group_id' : group_id })
        return cpps['owner']