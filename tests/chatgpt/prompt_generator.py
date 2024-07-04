from markdownify import markdownify


PROMPT_LENGTH_LIMIT = 16384
PROMPT_HEADROOM = 500
CUTOFF_MIN_MESSAGE_LENGTH = 140
SUMMARY_EXPECTED_LENGTH = 800


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


def html2markdown(content):
    return markdownify(content, strip=['a', 'img'])


def generate_embedding_prompt(review):
    header = get_user(review) + '在' + get_course(review.course) + '课程' + get_course_term(review) + '的点评：\n'
    return header + html2markdown(review.content).strip()


def generate_short_prompt(reviews, full_prompt):
    cutoff_ratio = PROMPT_LENGTH_LIMIT * 1.0 / len(full_prompt)
    prompt = ''
    for review in reviews:
        content = html2markdown(review.content).strip()
        if len(content) > CUTOFF_MIN_MESSAGE_LENGTH:
            cutoff_len = max(int(len(content) * cutoff_ratio), CUTOFF_MIN_MESSAGE_LENGTH)
            content = content[0:cutoff_len]
        prompt += get_user(review) + '的点评：' + content + '\n'
        if len(prompt) > PROMPT_LENGTH_LIMIT:
            return prompt[:PROMPT_LENGTH_LIMIT + PROMPT_HEADROOM]
    return prompt


def generate_summary_prompt(reviews):
    header = '根据下列点评，尽可能详细、全面地总结' + get_course(reviews[0].course) + '课程的考试、给分、作业、教学水平、课程内容等，800 字左右，以便让同学们更好地选课。尽量忠于点评内容，可以引用点评中的原句，点评中如果有写得特别精彩的句子建议引用。如果有冲突的观点，应客观总结双方的观点。\n\n'
    contents = [get_user(review) + '的点评：' + html2markdown(review.content).strip() for review in reviews]

    joined_contents = '\n'.join(contents)
    if len(joined_contents) <= SUMMARY_EXPECTED_LENGTH:
        return joined_contents

    full_prompt = header + joined_contents
    if len(full_prompt) <= PROMPT_LENGTH_LIMIT:
        return full_prompt
    else:
        return header + generate_short_prompt(reviews, full_prompt)
