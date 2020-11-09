from flask import current_app
from flask_login import UserMixin
from src import db, login_manager
from src.search import add_to_index, remove_from_index, query_index
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from datetime import datetime
from time import time
import json
import redis
import rq

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if not ids or total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(SearchableMixin, UserMixin, db.Model):
    __searchable__ = ['username', 'showname']

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    showname = db.Column(db.String(20), nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    email = db.Column(db.String(50), default='')
    password = db.Column(db.String(60), nullable=False)
    bio = db.Column(db.String(200), default='')
    created_utc = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    filter_nsfw = db.Column(db.Boolean, nullable=False, default=False)
    admin_level = db.Column(db.Integer, nullable=False, default=0)
    is_banned = db.Column(db.Boolean, nullable=False, default=False)

    tweets = db.relationship('Tweet', backref='author', lazy="dynamic")

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    liked = db.relationship(
        'Like',
        foreign_keys='Like.userid',
        backref='user', lazy='dynamic')

    messages_sent = db.relationship('Message',
        foreign_keys='Message.sender_id',
        backref='author', lazy='dynamic')
    messages_received = db.relationship('Message',
        foreign_keys='Message.recipient_id',
        backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)

    comments_sent = db.relationship('Comment',
        foreign_keys='Comment.commenter_id',
        backref='author', lazy='dynamic')
    comments_received = db.relationship('Comment',
        foreign_keys='Comment.author_id',
        backref='recipient', lazy='dynamic')
    last_notifs_read_time = db.Column(db.DateTime)

    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def followed_posts(self):
        followed = Tweet.query.join(
            followers, (followers.c.followed_id == Tweet.userid)).filter(followers.c.follower_id == self.id)
        own = Tweet.query.filter_by(userid=self.id)
        tweets = followed.union(own).order_by(Tweet.created_utc.desc())
        if self.filter_nsfw:
            tweets = tweets.filter_by(is_nsfw=False)
        return tweets

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def get_reset_token(self, expires_sec=900):
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    def like_tweet(self, tweet):
        if not self.has_liked_tweet(tweet):
            l = Like(userid=self.id, tweetid=tweet.id)
            db.session.add(l)

    def unlike_tweet(self, tweet):
        if self.has_liked_tweet(tweet):
            Like.query.filter(
                Like.userid==self.id,
                Like.tweetid==tweet.id).delete()

    def has_liked_tweet(self, tweet):
        return Like.query.filter(
            Like.userid==self.id,
            Like.tweetid==tweet.id).count() > 0

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(Message.created_utc > last_read_time).count()

    def new_notifs(self):
        last_read_time = self.last_notifs_read_time or datetime(1900, 1, 1)
        return Comment.query.filter_by(recipient=self).filter(Comment.created_utc > last_read_time, Comment.commenter_id != self.id).count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('src.tasks.' + name, self.id, *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self, complete=False).all()

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Tweet(SearchableMixin, db.Model):
    __searchable__ = ['textbody']

    id = db.Column(db.Integer, primary_key=True)
    textbody = db.Column(db.String(500), nullable=False)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='tweetComment', lazy="dynamic")
    created_utc = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    edited_utc = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    stickied = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    is_nsfw = db.Column(db.Boolean, default=False)
    is_edited = db.Column(db.Boolean, default=False)
    comment_path_counter = db.Column(db.Integer, default=1, autoincrement=True)

    likes = db.relationship('Like', backref='tweet', lazy='dynamic')

    def __repr__(self):
        return '<Tweet {}>'.format(self.textbody)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'))
    tweetid = db.Column(db.Integer, db.ForeignKey('tweet.id'))

    def __repr__(self):
        return '<Like {},{}>'.format(self.userid, self.tweetid)

class Comment(db.Model):
    _N = 6

    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # author of post
    commenter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # author of comment
    textbody = db.Column(db.String(400), nullable=False)
    created_utc = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    path = db.Column(db.Text, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic')

    def save(self):
        db.session.add(self)
        db.session.commit()
        prefix = self.parent.path + '.' if self.parent else ''
        self.tweetComment.comment_path_counter += 1
        self.path = prefix + '{:0{}d}'.format(self.tweetComment.comment_path_counter, self._N)
        db.session.commit()

    def level(self):
        return len(self.path)

    def __repr__(self):
        return '<Comment {}>'.format(self.id)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    created_utc = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))

class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100
