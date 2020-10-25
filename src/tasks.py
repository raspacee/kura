from src import create_app, db
from src.models import User, Tweet, Task
from src.email import send_email
from rq import get_current_job
import sys
import time
import json

app = create_app()
app.app_context().push()

def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress',
            {'task_id': job.get_id(),
            'progress': int(progress)})
        if progress >= 100:
            task.complete = True
        db.session.commit()

def export_posts(user_id):
    try:
        user = User.query.get(user_id)
        _set_task_progress(0)
        data = []
        i = 0
        total_tweets = user.tweets.count()
        for tweet in user.tweets.order_by(Tweet.created_utc.asc()):
            data.append({'body': tweet.textbody,
                        'created_utc': tweet.created_utc.isoformat() + 'Z'})
            time.sleep(3)
            i += 1
            _set_task_progress(100 * i / total_tweets)

        send_email('Your tweet posts',
            sender='noreply@demo.com',
            recipients=[user.email],
            text_body=f'''
                Dear {user.username},

                The archive of your posts that you requested is available.
                ''',
            attachments=[('posts.json', 'application/json', json.dumps({'posts': data}, indent=4))],
            sync=True)
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    finally:
        _set_task_progress(100)
