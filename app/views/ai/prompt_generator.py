from markdownify import markdownify


PROMPT_LENGTH_LIMIT = 32000
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


def generate_summary_prompt(reviews, expected_summary_length):
    course_name = get_course(reviews[0].course)
    header = f'根据下列点评，尽可能简洁、全面、客观地总结{course_name}课程的考试、给分、作业、教学水平、课程内容等，以便让同学们更好地选课。注意字数限制，{expected_summary_length} 字左右。尽量忠于点评内容，可以引用点评中的原句，点评中如果有写得特别精彩的句子建议引用。如果有冲突的观点，应客观总结双方的观点。不要说废话，不要胡编乱造。不需要全文大标题，只要分段小标题。\n\n'
    contents = []
    for review in reviews:
        markdown = html2markdown(review.content).strip()
        user_info = get_user(review)
        content = f'{user_info}的点评：\n=== 点评开始 ===\n{markdown}\n=== 点评结束 ==='
        contents.append(content)

    joined_contents = '\n\n'.join(contents)
    full_prompt = header + joined_contents
    if len(full_prompt) <= PROMPT_LENGTH_LIMIT:
        user_prompt = full_prompt
    else:
        user_prompt = header + generate_short_prompt(reviews, full_prompt)

    system_prompt = '你是 USTC 评课社区的一个课程总结助手，旨在为每门课程的点评生成简洁、客观、全面的总结。'
    return system_prompt, user_prompt
