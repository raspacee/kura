from flask import Flask, request, abort
from flask_sqlalchemy import SQLAlchemy, BaseQuery
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_moment import Moment
from src.config import Config
from redis import Redis
from elasticsearch import Elasticsearch
import rq

# class CustomBaseQuery(BaseQuery):
#     def user_get_or_404(self, ident):
#         user = self.filter_by(username=ident).first()
#         if not user:
#             abort(404)
#         return user

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
moment = Moment()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('kura-tasks', connection=app.redis)

    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
                        if app.config['ELASTICSEARCH_URL'] else None

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    migrate = Migrate(app, db)

    from src.main.routes import main
    from src.users.routes import users
    from src.tweets.routes import tweets
    from src.errors.handlers import errors

    app.register_blueprint(main)
    app.register_blueprint(users)
    app.register_blueprint(tweets)
    app.register_blueprint(errors)

    return app
