from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, ValidationError, Length

class CreateTweetForm(FlaskForm):
    textbody = TextAreaField('Body', validators=[DataRequired(), Length(min=1, max=500)])
    is_nsfw = BooleanField('This Post Contains NSFW Content')
    submit = SubmitField('Tweet')

class CreateCommentForm(FlaskForm):
    textbody = TextAreaField('Body', validators=[DataRequired(), Length(min=1, max=400)])
    submit = SubmitField('Comment')
