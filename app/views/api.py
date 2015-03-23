from flask import Blueprint,jsonify,request
from app.models import CourseReview as Review, CourseReviewComment as Comment, User

api = Blueprint('api',__name__)


@api.route('/review_upvote/',methods=['POST'])
def review_upvote():
    pass


@api.route('/review_comment/',methods=['POST'])
def post_review_comment():
    json = request.get_json
    if not json:
        return 404
    if 'id' not in json or 'content' not in 'json':
        return jsonify(status='Authentication failed')
    id = json.get('id')
    content = json.get('content')

    review = Review.query.get(id)
    comment = Comment(content=content)
    review.add_comment(comment)
    return jsonify(comment)



@api.route('/review_comment/',methods=['GET'])
def get_review_comment():
    id = request.args.get('id')
    if not id:
        return jsonify(status='Id not found')

    review = Review.query.get(id)
    if review:
        comments = review.comments
    else:
        return jsonify(status='Id not found',data=None)
    return jsonify(status='OK',data=comments)

@api.route('/reg_verify', methods=['GET'])
def reg_verify():
    name = request.args.get('name')
    value = request.args.get('value')

    if name == 'username':
        if User.query.filter_by(username=value).first():
            return 'Username Exists'
        return 'OK'
    elif name == 'email':
        if User.query.filter_by(email=value).first():
            return 'Email Exists'
        return 'OK'
    return 'Invalid Request', 400
