from flask import Blueprint,jsonify,request, Markup
from flask_login import login_required,current_user
from app.models import Review, ReviewComment , User, Course, ImageStore
from app.forms import ReviewCommentForm
from app.utils import rand_str, handle_upload, validate_username, validate_email
from app.utils import editor_parse_at
from app import app
import re
import os

api = Blueprint('api',__name__)


@api.route('/reviews/')
def get_reviews():
    response = {'ok':True,
            'info':'',
            'data': []
            }
    course_id = request.args.get('course_id',type=int)
    page = request.args.get('page',1,type=int)
    if not course_id:
        response['ok'] = False
        response['info'] = 'Need to specify a course id'
        return jsonify(response)
    course = Course.query.get(course_id)
    if not course:
        response['ok'] = False
        response['info'] = 'Course can\'t found'
        return jsonify(response)
    reviews = course.reviews.paginate(page)
    for item in reviews.items:
        review = {'id':item.id,
                'rate':item.rate,
                'content':item.content,
                'author':{'name':item.author.username,
                    'id':item.author_id},
                'upvote':item.upvote,
                }
        response['data'].append(review)
    return jsonify(response)


@api.route('/review/upvote/',methods=['POST'])
@login_required
def review_upvote():
    review_id = request.values.get('review_id')
    if review_id:
        review = Review.query.get(review_id)
        if review:
            ok,message = review.upvote()
            if ok:
                for user in set(current_user.followers + [review.author]):
                    user.notify('upvote', review)
            return jsonify(ok=ok,message=message, count=review.upvote_count)
        else:
            return jsonify(ok=False,message="The review doesn't exist.")
    else:
        return jsonify(ok=false,message="A id must be given")

@api.route('/review/cancel_upvote/',methods=['POST'])
@login_required
def review_cancel_upvote():
    review_id = request.values.get('review_id')
    if review_id:
        review = Review.query.get(review_id)
        if review:
            ok,message = review.cancel_upvote()
            return jsonify(ok=ok,message=message, count=review.upvote_count)
        else:
            return jsonify(ok=False,message="The review doesn't exist.")
    else:
        return jsonify(ok=False,message="A id must be given")

@api.route('/review/new_comment/',methods=['POST'])
@login_required
def review_new_comment():
    form = ReviewCommentForm(formdata=request.form)
    if form.validate_on_submit():
        review_id = request.form.get('review_id')
        if review_id:
            review = Review.query.get(review_id)
            comment = ReviewComment()
            content = request.form.get('content')
            if len(content) > 500:
                return jsonify(ok=False,message="评论太长了，不能超过 500 字哦")
            content = Markup(content).striptags()
            content, mentioned_users = editor_parse_at(content)
            ok,message = comment.add(review,content)
            if ok:
                for user in set(current_user.followers + [review.author]):
                    user.notify('comment', review)
                for user in mentioned_users:
                    user.notify('mention', comment)
            return jsonify(ok=ok,message=message,content=content)
        else:
            return jsonify(ok=False,message="The review doesn't exist.")
    else:
        return jsonify(ok=False,message=form.errors)


@api.route('/review/delete_comment/',methods=['POST'])
@login_required
def delete_comment():
    comment_id = request.values.get('comment_id')
    if comment_id:
        comment = ReviewComment.query.get(comment_id)
        if comment:
            if comment.author == current_user or current_user.is_admin:
                ok,message = comment.delete()
                return jsonify(ok=ok,message=message)
            else:
                return jsonify(ok=False,message="Forbidden")
        else:
            return jsonify(ok=False,message="The comment doesn't exist.")
    else:
        return jsonify(ok=False,message="A id must be given")

@api.route('/review/hide/', methods=['POST'])
@login_required
def hide_review():
    review_id = request.values.get('review_id')
    if review_id:
        review = Review.query.get(review_id)
        if review:
            if current_user.is_admin:
                ok,message = review.hide()
                return jsonify(ok=ok,message=message)
            else:
                return jsonify(ok=False,message="Forbidden")
        else:
            return jsonify(ok=False,message="The review doesn't exist.")
    else:
        return jsonify(ok=False,message="A id must be given")

@api.route('/review/unhide/', methods=['POST'])
@login_required
def unhide_review():
    review_id = request.values.get('review_id')
    if review_id:
        review = Review.query.get(review_id)
        if review:
            if current_user.is_admin:
                ok,message = review.unhide()
                return jsonify(ok=ok,message=message)
            else:
                return jsonify(ok=False,message="Forbidden")
        else:
            return jsonify(ok=False,message="The review doesn't exist.")
    else:
        return jsonify(ok=False,message="A id must be given")

@api.route('/user/follow/', methods=['POST'])
@login_required
def follow_user():
    user_id = request.values.get('user_id')
    user = User.query.get(user_id)
    if user:
        if user == current_user:
            return jsonify(ok=False, message='Cannot follow yourself')
        elif user in current_user.users_following:
            return jsonify(ok=False, message='You have already followed the specified user')
        current_user.follow(user)
        user.notify('follow', user)
        return jsonify(ok=True)
    else:
        return jsonify(ok=False, message='User does not exist')

@api.route('/user/unfollow/', methods=['POST'])
@login_required
def unfollow_user():
    user_id = request.values.get('user_id')
    user = User.query.get(user_id)
    if user:
        if user == current_user:
            return jsonify(ok=False, message='Cannot follow yourself')
        elif user not in current_user.users_following:
            return jsonify(ok=False, message='You have not followed the specified user')
        current_user.unfollow(user)
        return jsonify(ok=True)
    else:
        return jsonify(ok=False, message='User does not exist')

def generic_upload(file, type):
    ok,message = handle_upload(file, type)
    script_head = '<script type="text/javascript">window.parent.CKEDITOR.tools.callFunction(2,'
    script_tail = ');</script>'
    if ok:
        url = '/uploads/' + type + 's/' + message
        return script_head + '"' + url + '"' + script_tail
    else:
        return script_head + '""' + ',' + '"' + message + '"' + script_tail

@api.route('/upload/image',methods=['POST'])
@login_required
@app.csrf.exempt
def upload_image():
    return generic_upload(request.files['upload'], 'image')

@api.route('/upload/file', methods=['POST'])
@login_required
@app.csrf.exempt
def upload_file():
    return generic_upload(request.files['upload'], 'file')



@api.route('/reg_verify', methods=['GET'])
def reg_verify():
    name = request.args.get('name')
    value = request.args.get('value')

    if name == 'username':
        return validate_username(value)
    elif name == 'email':
        return validate_email(value)
    return 'Invalid Request', 400

@api.route('/notifications/', methods=['POST'])
@login_required
def read_notifications():
    current_user.unread_notification_count = 0
    current_user.save()
    return jsonify(ok=True)

