# Internal imports
from will.API import v1

# Builtin imports
import logging

log = logging.getLogger()

base_path = "/api/{version_num}"

routes = {
    "oauth2": {
        "route": "/oauth2/{step_id}",
        "versions":
            {
                "v1": v1.Oauth2()
            }
    },
    "users": {
        "route": "/users/{username}",
        "versions":
            {
                "v1": v1.Users()
            }
    },
    "sessions": {
        "route": "/sessions/{session_id}",
        "versions": {
            "v1": v1.Sessions()
        }
    },
    "clients": {
        "route": "/clients",
        "versions": {
            "v1": v1.Sessions()
        }
    },
    "commands": {
        "route": "/commands",
        "versions": {
            "v1": v1.Sessions()
        }
    }
}

def process_routes(app):
    """
    Add routes to the api for every url
    
    :param app: Falcon app instance
    """
    for route, route_data in routes.items():
        for version, version_instance in route_data["versions"].items():
            path = base_path.format(version_num=version)+route_data["route"]
            log.info("Processing route {0}".format(path))
            app.add_route(path, version_instance)