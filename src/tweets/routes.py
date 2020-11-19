from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from src import db
from src.models import User, Tweet, Like, Comment
from src.tweets.forms import CreateTweetForm, CreateCommentForm
import markdown2
import bleach

tweets = Blueprint('tweets', __name__)

@tweets.route("/tweet/create", methods=['GET', 'POST'])
@login_required
def tweet_create():
    form = CreateTweetForm()
    if form.validate_on_submit():
        time = datetime.utcnow()
        markdown = markdown2.markdown(form.textbody.data)
        bleached_markdown = bleach.clean(markdown, tags=['b', 'i', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'abbr', 'acronym', 'p', 'code', 'blockquote', 'table', 'tr', 'td', 'br', 'ol', 'li', 'pre', 'div', 'span', 'em', 'strong', 'cite', 'col', 'colgroup', 'datalist', 'dd', 'dt', 'dl', 'q', 's', 'small', 'sub', 'sup', 'td', 'tbody', 'th', 'thead', 'u'])
        tweet = Tweet(identifier=Tweet.get_identifier(), textbody_source=form.textbody.data, textbody_markdown=bleached_markdown, author=current_user, created_utc=time, is_nsfw=form.is_nsfw.data)
        db.session.add(tweet)
        db.session.commit()
        return redirect(url_for('main.home'))
    return render_template('tweets/tweet_create.html', title='Create a tweet', form=form)

@tweets.route("/tweet/<string:ident>")
@login_required
def tweet_show(ident):
    tweet = Tweet.query.filter_by(identifier=ident).first_or_404()
    comments = tweet.comments.filter(Comment.parent == None).all()
    return render_template('tweets/tweet.html', tweet=tweet, comments=comments, showCreateComment=True)

@tweets.route("/tweet/<string:ident>/edit", methods=['GET', 'POST'])
@login_required
def tweet_edit(ident):
    tweet = Tweet.query.filter_by(identifier=ident).first_or_404()
    if current_user.id != tweet.userid:
        abort(403)
    form = CreateTweetForm()
    if form.validate_on_submit():
        tweet.textbody_source = form.textbody.data
        tweet.textbody_markdown = markdown2.markdown(form.textbody.data)
        edited_time = datetime.utcnow()
        tweet.edited_utc = edited_time
        tweet.is_edited = True
        tweet.is_nsfw = form.is_nsfw.data
        db.session.commit()
        return redirect(url_for('main.home'))
    elif request.method == 'GET':
        form.textbody.data = tweet.textbody_source
        form.is_nsfw.data = tweet.is_nsfw
    return render_template('tweets/tweet_create.html', form=form, is_editing=True)

@tweets.route("/tweet/like", methods=['POST'])
def tweet_like():
    if not current_user.is_authenticated:
        response = {"statuscode": -1, "status": "Permission denied"}
        return jsonify(response)

    tweet_ident = request.json['ident']
    tweet = Tweet.query.filter_by(identifier=tweet_ident).first()
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
    if not current_user.is_authenticated:
        response = {"statuscode": -1, "status": "Permission denied"}
        return jsonify(response)

    tweet_ident = request.json['ident']
    tweet = Tweet.query.filter_by(identifier=tweet_ident).first()
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

@tweets.route("/tweet/<string:ident>/comment/create", methods=['GET', 'POST'])
@login_required
def comment_create(ident):
    form = CreateCommentForm()
    tweet = Tweet.query.filter_by(identifier=ident).first_or_404()
    if form.validate_on_submit():
        comment = Comment(textbody=form.textbody.data, identifier=Comment.get_identifier(), tweet=tweet, author=current_user, recipient=tweet.author)
        comment.save()
        tweet.author.add_notification('unread_notifs_count', tweet.author.new_notifs())
        db.session.commit()
        return redirect(url_for('tweets.tweet_show', ident=ident))
    return render_template('tweets/comment_create.html', form=form)

@tweets.route("/comment/<string:ident>/replies", methods=['GET'])
@login_required
def comment_replies(ident):
    comment = Comment.query.filter_by(identifier=ident).first_or_404()
    return render_template('tweets/replies.html', comment=comment)

@tweets.route("/comment/<string:ident>/reply", methods=['GET', 'POST'])
@login_required
def comment_reply(ident):
    form = CreateCommentForm()
    p_comment = Comment.query.filter_by(identifier=ident).first_or_404()
    if form.validate_on_submit():
        comment = Comment(textbody=form.textbody.data, identifier=Comment.get_identifier(), tweet=p_comment.tweet, author=current_user, recipient=p_comment.tweet.author, parent=p_comment)
        comment.save()
        p_comment.author.add_notification('unread_notifs_count', p_comment.author.new_notifs())
        db.session.commit()
        return redirect(url_for('tweets.comment_replies', ident=p_comment.identifier))
    return render_template('tweets/comment_create.html', form=form, is_reply=True)
