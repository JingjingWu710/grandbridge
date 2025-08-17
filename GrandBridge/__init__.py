from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import calendar as py_calendar
import os
from dotenv import load_dotenv
load_dotenv()
from GrandBridge.config import Config

# print("DEBUG ENV VARS:")
# for k, v in os.environ.items():
#     if "GOOGLE" in k:
#         print(f"{k} = {v}")

app = Flask(__name__)
# >>> import secrets
# >>> secrets.token_hex(16)
# 'd84d5540915408f9f2a942d2fcc5da75'
app.config['SECRET_KEY'] = '3b44602dd40bad51c6ba5acd518c0558'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.path.join('GrandBridge', 'static', 'uploads')
app.config.from_object(Config)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'

@app.template_filter('month_name')
def month_name_filter(month):
    return py_calendar.month_name[month]

from GrandBridge.users.routes import users
from GrandBridge.calendar.routes import calendar
from GrandBridge.main.routes import main
from GrandBridge.planting.routes import planting
from GrandBridge.foodmap.routes import foodmap
from GrandBridge.memory.routes import memory
from GrandBridge.nutrition.routes import nutrition
from GrandBridge.community.routes import community
from GrandBridge.chatroom.routes import chatroom

app.register_blueprint(users)
app.register_blueprint(calendar)
app.register_blueprint(main)
app.register_blueprint(planting)
app.register_blueprint(foodmap)
app.register_blueprint(memory)
app.register_blueprint(nutrition)
app.register_blueprint(community)
app.register_blueprint(chatroom)