from flask import Flask, Blueprint
from apis import api

import os

# instantiate the app
app = Flask(__name__)

# set config
app_settings = os.getenv('APP_SETTINGS')
app.config.from_object(app_settings)


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)

def initialize_app(flask_app):
    blueprint = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(blueprint)

    # register blueprints
    # flask_app.register_blueprint(views.customers)
    flask_app.register_blueprint(blueprint)


def main():
    initialize_app(app)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
