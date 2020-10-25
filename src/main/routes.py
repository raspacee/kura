from flask import Blueprint, render_template, redirect, request, current_app, url_for, g
from flask_login import current_user
from sqlalchemy import or_
from src.models import db, Tweet, User
from src.main.forms import SearchForm

main = Blueprint('main', __name__)

@main.before_app_request
def before_request():
    if current_user.is_authenticated:
        g.search_form = SearchForm()

@main.route("/")
@main.route("/home")
def home():
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        tweets = current_user.followed_posts().paginate(
            page, current_app.config['TWEETS_PER_PAGE'], False)
        next_url = url_for('main.home', page=tweets.next_num) if tweets.has_next else None
        prev_url = url_for('main.home', page=tweets.prev_num) if tweets.has_prev else None
        return render_template('home.html', tweets=tweets.items, showCreateTweet=True, next_url=next_url, prev_url=prev_url)
    return render_template('home.html', emptyTweets=True, showCreateTweet=True)

@main.route("/search", methods=['GET'])
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.home'))
    query = g.search_form.q.data
    page = request.args.get('page', 1, type=int)
    tweets, total_tweets = Tweet.search(query, page, 3)
    if current_user.is_anonymous or current_user.filter_nsfw:
        tweets = tweets.filter_by(is_nsfw=False).all()
    users, total_users = User.search(query, page, 3)
    if current_user.is_authenticated:
        users = users.filter(User.id != current_user.id)

    next_url = url_for('main.search', q=query, page=page + 1) if total_tweets > page * 3 else None
    prev_url = url_for('main.search', q=query, page=page - 1) if page > 1 else None
    return render_template('search_results.html', tweets=tweets, users=users, query=query, next_url=next_url, prev_url=prev_url, total_tweets=total_tweets, total_users=total_users)
