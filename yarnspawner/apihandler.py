import json
from tornado import web
from jupyterhub.apihandlers import APIHandler, default_handlers


# Borrowed and modified from jupyterhub/batchspawner:
# https://github.com/jupyterhub/batchspawner/blob/d5f9a0bbaa92748267bb1dd2cc4d4a0436670482/batchspawner/api.py
class YarnSpawnerAPIHandler(APIHandler):
    @web.authenticated
    def post(self):
        """POST set user spawner data"""
        if hasattr(self, "current_user"):
            # Jupyterhub compatability, (september 2018, d79a99323ef1d)
            user = self.current_user
        else:
            # Previous jupyterhub, 0.9.4 and before.
            user = self.get_current_user()
        token = self.get_auth_token()
        spawner = None
        for s in user.spawners.values():
            if s.api_token == token:
                spawner = s
                break
        data = self.get_json_body()
        for key, value in data.items():
            if hasattr(spawner, key):
                setattr(spawner, key, value)
        self.finish(json.dumps({"message": "YarnSpawner data configured"}))
        self.set_status(201)


default_handlers.append((r"/api/yarnspawner", YarnSpawnerAPIHandler))
