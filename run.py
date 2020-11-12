from src import create_app, db
from src.models import User, Tweet, Notification, Message, Task, Comment

app = create_app()

@app.after_request
def apply_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Tweet': Tweet, 'Message': Message, 'Comment': Comment, 'Notification': Notification, 'Task': Task}

if __name__ == '__main__':
    app.run(debug=True)
