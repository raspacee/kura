from flask import Blueprint, render_template, redirect, flash, url_for, request, jsonify, abort, current_app
from flask_login import current_user, login_user, login_required, logout_user
from datetime import datetime
from src import db, bcrypt
from src.models import User, Tweet, Message, Notification, Comment
from src.users.forms import SignupForm, LoginForm, UserSettingsForm, RequestResetForm, ResetPasswordForm, MessageForm
from src.users.utils import save_picture, send_reset_email

users = Blueprint('users', __name__)

@users.route("/signup", methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = SignupForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            time = datetime.utcnow()
            user = User(username=form.username.data, showname=form.showname.data, email=form.email.data, password=hashed_password, created_utc=time)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created. Login Now', 'success')
            return redirect(url_for('main.home'))
        except Exception as e:
            flash(e, 'error')
    return render_template('users/signup.html', title='Sign Up', form=form)

@users.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return(redirect(url_for('main.home')))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('Successfully logged in', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Incorrect username or password', 'danger')
    return render_template('users/login.html', title='Login', form=form)

@users.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('users.login'))

@users.route("/user/<string:username>/profile")
@login_required
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    tweets = user.tweets.filter_by(stickied=False).order_by(Tweet.created_utc.desc())
    if current_user.filter_nsfw:
        tweets = tweets.filter_by(is_nsfw=False)
    tweets = tweets.paginate(
        page, current_app.config['TWEETS_PER_PAGE'], False)
    next_url = url_for('users.user_profile', username=username.id, page=tweets.next_num) if tweets.has_next else None
    prev_url = url_for('users.user_profile', username=username.id, page=tweets.prev_num) if tweets.has_prev else None
    stickytweets = user.tweets.filter_by(stickied=True).order_by(Tweet.created_utc.desc())
    if current_user.filter_nsfw:
        stickytweets = stickytweets.filter_by(is_nsfw=False)
    return render_template('users/profile.html', user=user, tweets=tweets.items, next_url=next_url, prev_url=prev_url, stickytweets=stickytweets.all())

@users.route("/user/settings", methods=['GET', 'POST'])
def user_setting():
    if not current_user.is_authenticated:
        abort(403)

    form = UserSettingsForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data, current_user.image_file)
            current_user.image_file = picture_file
        current_user.showname = form.showname.data
        current_user.email = form.email.data
        current_user.bio = form.bio.data
        current_user.filter_nsfw = form.filter_nsfw.data
        db.session.commit()
        return redirect(url_for('main.home'))
    elif request.method == 'GET':
        form.email.data = current_user.email
        form.showname.data = current_user.showname
        form.bio.data = current_user.bio
        form.filter_nsfw.data = current_user.filter_nsfw
    return render_template('users/settings.html', user=current_user, form=form)

@users.route("/user/follow", methods=['POST'])
def user_follow():
    if not current_user.is_authenticated:
        response = {"statuscode": -1, "status": "Permission denied"}
        return jsonify(response)

    master_username = request.json['username']
    user = User.query.filter_by(username=master_username).first()
    if not user or current_user.id == user.id:
        response = {"statuscode": -1, "status": "User not found or can't follow yourself"}
    else:
        if current_user.is_following(user):
            current_user.unfollow(user)
            response = {"statuscode": 0, "status": "Following"}
        else:
            current_user.follow(user)
            response = {"statuscode": 0, "status": "Unfollowed"}
        db.session.commit()
    return jsonify(response)

@users.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password. Check your email inbox', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been changd! Login Now', 'success')
        return redirect(url_for('users.login'))
    return render_template('reset_token.html', form=form)

@users.route('/send_message/<string:recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user, body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash('Your message has been sent', 'success')
        return redirect(url_for('users.user_profile', username=user.username))
    return render_template('users/send_message.html', form=form, recipient=recipient)

@users.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    messages = current_user.messages_received.order_by(Message.created_utc.desc()).all()
    return render_template('users/messages.html', messages=messages)

@users.route('/notifs')
@login_required
def notifs():
    current_user.last_notifs_read_time = datetime.utcnow()
    current_user.add_notification('unread_notifs_count', 0)
    db.session.commit()
    comments = current_user.comments_received.filter(Comment.commenter_id != current_user.id).order_by(Comment.created_utc.desc()).all()
    return render_template('users/notifs.html', comments=comments)


@users.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
        } for n in notifications])

@users.route('/export_posts')
@login_required
def export_posts():
    if current_user.email == '':
        flash('You need to add a email before exporting your tweets', 'info')
        return redirect(url_for('users.user_profile', user_id=current_user.id))
    if current_user.get_task_in_progress('export_posts'):
        flash('An export task is currently in progress. Please wait', 'info')
    else:
        current_user.launch_task('export_posts', 'Exporting tweets')
        db.session.commit()
    return redirect(url_for('users.user_profile', user_id=current_user.id))
