from tornado import web
from jupyterhub.apihandlers import APIHandler, default_handlers


# Borrowed and modified from jupyterhub/batchspawner:
# https://github.com/jupyterhub/batchspawner/blob/d1052385f2/batchspawner/api.py
class YarnSpawnerAPIHandler(APIHandler):
    @web.authenticated
    def post(self):
        """POST set user's spawner port number"""
        user = self.current_user
        data = self.get_json_body()
        port = int(data.get('port', 0))
        name = data.get('name', '')

        self.log.debug("Registering port number %i for spawner '%s' of user '%s'", port, name, user.name)

        resp_code = 201
        resp_body = {"message": "YarnSpawner port configured"}
        if name:
            # if allow_named_servers
            if name in user.spawners:
                user.spawners[name].current_port = port
            else:
                resp_code = 400
                resp_body = {"message": "YarnSpawner not found for named server {}".format(name)}
        else:
            user.spawner.current_port = port

        self.finish(resp_body)
        self.set_status(resp_code)


default_handlers.append((r"/api/yarnspawner", YarnSpawnerAPIHandler))
