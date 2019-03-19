from flask import Flask, Blueprint
from apis import api

import os

# instantiate the app
app = Flask(__name__)

# set config
app_settings = os.getenv('APP_SETTINGS')
app.config.from_object(app_settings)


def initialize_app(flask_app):
    blueprint = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(blueprint)

    # register blueprints
    # flask_app.register_blueprint(views.customers)
    flask_app.register_blueprint(blueprint)


def main():
    initialize_app(app)

    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
