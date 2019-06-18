import json
from tornado import web
from jupyterhub.apihandlers import APIHandler, default_handlers


# Borrowed and modified from jupyterhub/batchspawner:
# https://github.com/jupyterhub/batchspawner/blob/d1052385f2/batchspawner/api.py
class YarnSpawnerAPIHandler(APIHandler):
    @web.authenticated
    def post(self):
        """POST set user's spawner port number"""
        user = self.self.current_user
        data = self.get_json_body()
        port = int(data.get('port', 0))
        user.spawner.current_port = port
        self.finish(json.dumps({"message": "YarnSpawner port configured"}))
        self.set_status(201)


default_handlers.append((r"/api/yarnspawner", YarnSpawnerAPIHandler))
