# Internal imports
from will.API import v1

# Builtin imports
import logging

log = logging.getLogger()

base_path = "/api/{version_num}"

routes = {
    "access_token": {
        "routes": ["/oauth2/access_token"],
        "versions":
            {
                "v1": v1.AccessToken()
            }
    },
    "user_token":{
        "routes": ["/oauth2/user_token"],
        "versions":
            {
                "v1": v1.UserToken()
            }
    },
    "users": {
        "routes":
            ["/users/{username}", "/users"],
        "versions":
            {
                "v1": v1.Users()
            }
    },
    "sessions": {
        "routes":
            ["/sessions/{session_id}", "/sessions"],
        "versions": {
            "v1": v1.Sessions()
        }
    },
    "clients": {
        "routes": ["/clients"],
        "versions": {
            "v1": v1.Sessions()
        }
    },
    "commands": {
        "routes": ["/commands"],
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
            for route in route_data["routes"]:
                path = base_path.format(version_num=version)+route
                log.info("Processing route {0}".format(path))
                app.add_route(path, version_instance)