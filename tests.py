#!/flask/bin/python

from datetime import datetime, timedelta
import unittest
from src import create_app
from src.models import db, User, Tweet, Comment

app = create_app()
app.app_context().push()

class UserModelCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_follow(self):
        u1 = User(username='john', showname='john', password='jpfkdjsd')
        u2 = User(username='susan', showname='susan', password='jpfkdjsd')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        self.assertEqual(u1.followed.all(), [])
        self.assertEqual(u1.followers.all(), [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 1)
        self.assertEqual(u1.followed.first().username, 'susan')
        self.assertEqual(u2.followers.count(), 1)
        self.assertEqual(u2.followers.first().username, 'john')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

    def test_follow_posts(self):
        u1 = User(username='john', showname='john', password='jpfkdjsd')
        u2 = User(username='susan', showname='susan', password='jpfkdjsd')
        u3 = User(username='mary', showname='susan', password='jpfkdjsd')
        u4 = User(username='david', showname='susan', password='jpfkdjsd')
        db.session.add_all([u1, u2, u3, u4])

        now = datetime.utcnow()
        t1 = Tweet(textbody="post from john", author=u1, created_utc=now + timedelta(seconds=1))
        t2 = Tweet(textbody="post from susan", author=u2, created_utc=now + timedelta(seconds=4))
        t3 = Tweet(textbody="post from mary", author=u3, created_utc=now + timedelta(seconds=3))
        t4 = Tweet(textbody="post from david", author=u4, created_utc=now + timedelta(seconds=2))
        db.session.add_all([t1, t2, t3, t4])
        db.session.commit()

        u1.follow(u2)
        u1.follow(u4)
        u2.follow(u3)
        u3.follow(u4)
        db.session.commit()

        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        self.assertEqual(f1, [t2, t4, t1])
        self.assertEqual(f2, [t2, t3])
        self.assertEqual(f3, [t3, t4])
        self.assertEqual(f4, [t4])

    def test_likes(self):
        u1 = User(username='bijay', showname='bijay', password='jfjdlkjfds')
        db.session.add(u1)

        now = datetime.utcnow()
        t1 = Tweet(textbody="post from bijay", author=u1, created_utc=now)
        db.session.add(t1)
        db.session.commit()

        self.assertEqual(t1.likes.count(), 0)

        u1.like_tweet(t1)
        db.session.commit()

        self.assertEqual(t1.likes.count(), 1)

        u1.unlike_tweet(t1)
        db.session.commit()

        self.assertEqual(t1.likes.count(), 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)

