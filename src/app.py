import os
import yaml

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

with open(os.environ['MIDDLEMAN_CONFIG']) as f:
    config_file = yaml.safe_load(f)


app = Flask('MiddleMan')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://{user}:{pass}@{ip}:{port}/{db}".format(**config_file['database'])

db = SQLAlchemy(app)
migrate = Migrate(app, db)


import controller

app.register_blueprint(controller.app)


if __name__ == "__main__":
    app.run()
