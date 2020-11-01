from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from src import db
from src.models import User, Tweet, Like, Comment
from src.tweets.forms import CreateTweetForm, CreateCommentForm

tweets = Blueprint('tweets', __name__)

@tweets.route("/tweet/create", methods=['GET', 'POST'])
@login_required
def tweet_create():
    form = CreateTweetForm()
    if form.validate_on_submit():
        time = datetime.utcnow()
        tweet = Tweet(textbody=form.textbody.data, author=current_user, created_utc=time, is_nsfw=form.is_nsfw.data)
        db.session.add(tweet)
        db.session.commit()
        return redirect(url_for('main.home'))
    return render_template('tweets/tweet_create.html', title='Create a tweet', form=form)

@tweets.route("/tweet/<int:tweet_id>")
@login_required
def tweet_show(tweet_id):
    tweet = Tweet.query.filter_by(id=tweet_id).first()
    comments = tweet.comments.filter(Comment.parent == None).all()
    return render_template('tweets/tweet.html', tweet=tweet, comments=comments, showCreateComment=True)

@tweets.route("/tweet/<int:tweet_id>/edit", methods=['GET', 'POST'])
@login_required
def tweet_edit(tweet_id):
    tweet = Tweet.query.filter_by(id=tweet_id).first()
    if not tweet or current_user.id != tweet.userid:
        return redirect(url_for('main.home'))
    form = CreateTweetForm()
    if form.validate_on_submit():
        tweet.textbody = form.textbody.data
        edited_time = datetime.utcnow()
        tweet.edited_utc = edited_time
        tweet.is_edited = True
        tweet.is_nsfw = form.is_nsfw.data
        db.session.commit()
        return redirect(url_for('main.home'))
    elif request.method == 'GET':
        form.textbody.data = tweet.textbody
        form.is_nsfw.data = tweet.is_nsfw
    return render_template('tweets/tweet_create.html', form=form, is_editing=True)

@tweets.route("/tweet/like", methods=['POST'])
def tweet_like():
    if not current_user.is_authenticated:
        response = {"statuscode": -1, "status": "Permission denied"}
        return jsonify(response)

    tweetid = request.json['tweet_id']
    tweet = Tweet.query.filter_by(id=tweetid).first()
    if not tweet:
        response = {"statuscode": -1, "status": "Tweet not found"}
    else:
        if current_user.has_liked_tweet(tweet):
            current_user.unlike_tweet(tweet)
            response = {"statuscode": 0, "status": "Liked"}
        else:
            current_user.like_tweet(tweet)
            response = {"statuscode": 0, "status": "Unliked"}
        db.session.commit()
    return jsonify(response)

@tweets.route("/tweet/sticky", methods=['POST'])
@login_required
def tweet_sticky():
    tweet_id = request.json['tweet_id']
    tweet = Tweet.query.filter_by(id=tweet_id).first()
    if tweet.userid == current_user.id:
        tweet.stickied = not tweet.stickied
        db.session.commit()
        response = {"statuscode": 0}
        return jsonify(response)
    else:
        response = {"statuscode": -1, "status": "Cannot sticky/unsticky the tweet"}
        return jsonify(response)
    response = {"statuscode": -1}
    return jsonify(response)

@tweets.route("/tweet/<int:tweet_id>/comment/create", methods=['GET', 'POST'])
@login_required
def comment_create(tweet_id):
    form = CreateCommentForm()
    tweet = Tweet.query.filter_by(id=tweet_id).first()
    if not tweet:
        return redirect(url_for('main.home'))
    if form.validate_on_submit():
        comment = Comment(textbody=form.textbody.data, tweetComment=tweet, author=current_user, recipient=tweet.author)
        comment.save()
        tweet.author.add_notification('unread_notifs_count', tweet.author.new_notifs())
        db.session.commit()
        return redirect(url_for('tweets.tweet_show', tweet_id=tweet_id))
    return render_template('tweets/comment_create.html', form=form)

@tweets.route("/comment/<int:comment_id>/replies", methods=['GET'])
@login_required
def comment_replies(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if not comment:
        return redirect(url_for('main.home'))
    return render_template('tweets/replies.html', comment=comment)

@tweets.route("/comment/<int:comment_id>/reply", methods=['GET', 'POST'])
@login_required
def comment_reply(comment_id):
    form = CreateCommentForm()
    p_comment = Comment.query.filter_by(id=comment_id).first()
    if not p_comment:
        return redirect(url_for('main.home'))
    if form.validate_on_submit():
        comment = Comment(textbody=form.textbody.data, tweetComment=p_comment.tweetComment, author=current_user, recipient=p_comment.tweetComment.author, parent=p_comment)
        comment.save()
        p_comment.author.add_notification('unread_notifs_count', p_comment.author.new_notifs())
        db.session.commit()
        return redirect(url_for('tweets.tweet_show', tweet_id=p_comment.tweetComment.id))
    return render_template('tweets/comment_create.html', form=form, is_reply=True)
