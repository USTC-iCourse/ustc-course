from markdownify import markdownify


def get_user(review):
    if review.is_anonymous:
        return '匿名用户'
    else:
        return '用户"' + review.author.username + '"'


def get_course(course):
    if len(course.teachers) == 0:
        return '《' + course.name + '》'
    else:
        teachers = sorted([ teacher.name for teacher in course.teachers ])
        return '、'.join(teachers) + '老师的《' + course.name + '》'


def get_course_term(review):
    if review.term_display == '未知':
        return ''
    else:
        return review.term_display + '季学期'


def html_to_markdown(content):
    return markdownify(content, strip=['a', 'img'])


def generate_embedding_prompt(review):
    header = get_user(review) + '在' + get_course(review.course) + '课程' + get_course_term(review) + '的点评：\n'
    return header + html_to_markdown(review.content)
