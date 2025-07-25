from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from flask_login import login_required
from app.models import Program
from app import db

program = Blueprint('program', __name__)

# key1: { key2: [value1, value2] } }
# value1 and value2 are sorted by sort_key
def add_to_2_level_dict(root, key1, key2, value, sort_key):
    if key1 in root:
        if key2 in root[key1]:
            root[key1][key2].append(value)
            root[key1][key2].sort(key=sort_key, reverse=True)
        else:
            root[key1][key2] = [value]
    else:
        root[key1] = {key2: [value]}

@program.route('/')
def index():
    programs = Program.query.all()
    program_dict = {}
    for program in programs:
        add_to_2_level_dict(program_dict, program.dept, program.name, program, lambda program: program.grade)
    return render_template('program-list.html', title='培养方案列表', programs=program_dict)

@program.route('/<int:program_id>/')
def view_program(program_id):
    program = Program.query.filter_by(id=program_id).first()
    if not program:
        abort(404)

    highlight_course_id = request.args.get('highlight_course')
    if highlight_course_id:
        try:
            # Handle cases where the value might contain extra characters or be malformed
            # Extract only the numeric part if there are query parameters included
            if '?' in highlight_course_id:
                highlight_course_id = highlight_course_id.split('?')[0]
            highlight_course_id = int(highlight_course_id)
        except (ValueError, TypeError):
            # If conversion fails, just ignore the highlight parameter
            highlight_course_id = None
    else:
        highlight_course_id = None

    title = program.name + '培养方案'

    return render_template('program.html', title=title, program=program, highlight_course_id=highlight_course_id)
