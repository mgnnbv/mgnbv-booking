from flask import Flask
from flask import db, User


app = Flask(__name__)
db.init_app(app)

@app.route('/get_all_tasks')
def get_all_tasks():
    users = User.query.all()
    return users