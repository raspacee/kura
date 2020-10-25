from src import create_app, db
from src.models import User, Tweet, Notification, Message, Task

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Tweet': Tweet, 'Message': Message, 'Notification': Notification, 'Task': Task}

if __name__ == '__main__':
    app.run(debug=True)
