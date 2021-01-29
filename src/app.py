import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


app = Flask('MiddleMan')
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:postgres@localhost:5432/middle_man"

db = SQLAlchemy(app)
migrate = Migrate(app, db)


import controller

app.register_blueprint(controller.app)


if __name__ == "__main__":
    app.run()
