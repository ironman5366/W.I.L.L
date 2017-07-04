# Internal imports
import will
from will.exceptions import *

# Builtin imports
import json
import os
import sys

cache = False

# Handle parameters
if "--cache" in sys.argv[1:]:
    cache = True

if "--destroy-cache" in sys.argv[1:]:
    if os.path.isfile("will.conf"):
        print("Destroying cached configuration")
        os.remove("will.conf")
    else:
        print("No cached configuration found, doing nothing")

def load_templates(
        db_url=os.getenv("DB_URL"),
        db_username=os.getenv("DB_USERNAME"),
        db_password=os.getenv("DB_PASSWORD"),
        secret_key=os.getenv("SECRET_KEY")):
    """
    Process templates from configs/*.conf, using environment variables to fill in sensitive data
    
    :param db_url: The url of the mysql instance
    :param db_username: The mysql username
    :param db_password: The mysql password
    :param secret_key: The key that will be used for itsdangerous HMAC signing in the API
    :return file_templates: A dictionary of the configuration templates, structured like so -
    {"prod": '{"db": "username": "neo4j"...}, "dev": {...}}
    """
    print ("Got db url {}".format(db_url))
    files = [f for f in os.listdir("configs") if f.endswith(".conf")]
    file_templates = {}
    for conf_file in files:
        branch_name = conf_file.split(".conf")[0]
        print("Creating configuration for branch {}".format(branch_name))
        conf_raw = open("configs/{}".format(conf_file)).read()

        # Assert that the data is valid JSON
        try:
            # Format the text with sensitive data
            conf_data = json.loads(conf_raw)
            conf_data["db"]["host"] = conf_data["db"]["host"].format(db_url=db_url)
            conf_data["db"]["user"] = conf_data["db"]["user"].format(db_username=db_username)
            conf_data["db"]["password"] = conf_data["db"]["password"].format(db_pass=db_password)
            conf_data["secret-key"] = conf_data["secret-key"].format(signing_key=secret_key)
            conf_data_text = json.dumps(conf_data)
            file_templates.update({branch_name: conf_data_text})
        except json.JSONDecodeError:
            raise ConfigurationError("Configuration template {0} raised a JSON Decode error".format(branch_name))
    return file_templates


def render_template(file_templates, branch=None):
    """
    Pick which templates to use, and load it
    :param file_templates: 
    :param branch: 
    :return found_template: The configuration template that will be loaded into W.I.L.L 
    """
    # If running in travis
    if not branch:
        if os.getenv("TRAVIS_BRANCH"):
            branch = os.getenv("TRAVIS_BRANCH")
        else:
            if os.getenv("BRANCH"):
                branch = os.getenv("BRANCH")
            else:
                print("Couldn't find branch in environment variables. Defaulting to dev")
                branch = "dev"
    if branch in file_templates.keys():
        found_template = file_templates[branch]
        return found_template
    else:
        raise ConfigurationError("Couldn't find branch {} in loaded templates".format(branch))

if os.path.isfile("will.conf"):
    # If the configuration has already been cached, serve it
    print("Using cached configuration...")
    conf = open("will.conf").read()
else:
    templates = load_templates()
    conf = render_template(templates)
    # Optionally save the found template so it doesn't have to be loaded every time
    if cache:
        print("Caching loaded configuration")
        conf_file = open("will.conf", 'w')
        conf_file.write(conf)
        conf_file.close()

os.chdir("will")

Will = will.will(conf_data=conf)

api = Will.app
