import json
from pathlib import Path

class RBAC:
    def __init__(self, config_path='config/rbac.json'):
        self.config_path = Path(config_path)
        self.acm = self.load_acm()

    def load_acm(self):
        """Load the Access Control Matrix from a JSON file."""
        if not self.config_path.exists():
            print(f"RBAC config file {self.config_path} not found. Initializing empty ACM.")
            return {}
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def save_acm(self):
        """Persist the current ACM back to the JSON file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.acm, f, indent=2)

    def can_invoke(self, actor, service):
        """Check if an actor can invoke a service."""
        permissions = self.acm.get(actor, {})
        return permissions.get(service, 'none') == 'invoke'

    def add_permission(self, actor, service, permission):
        """Add or update permission for an actor on a service."""
        if permission not in ['invoke', 'none']:
            raise ValueError("Permission must be 'invoke' or 'none'")
        if actor not in self.acm:
            self.acm[actor] = {}
        self.acm[actor][service] = permission
        self.save_acm()

    def remove_permission(self, actor, service):
        """Remove permission for an actor on a service."""
        if actor in self.acm and service in self.acm[actor]:
            del self.acm[actor][service]
            self.save_acm()

    def list_permissions(self, actor):
        """List all permissions for an actor."""
        return self.acm.get(actor, {})

    def list_all(self):
        """List all actors and their permissions."""
        return self.acm