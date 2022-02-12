import json
import collections

# Opening JSON file
f = open('/Users/cyf/Documents/GitHub/sustc-course/course-raw-data/2020-1.json')

# returns JSON object as
# a dictionary
data = json.load(f)
hash_list = []
hash_list_data = []
op_json = []
for c in data['rwList']['list']:
    teacher = sorted(c['dgjsmc'].split(',')) if c['dgjsmc'] else ['未知教师']
    no = c['kcdm']
    chash = str(teacher) + "-" + str(no)
    hash_list_data.append(chash)
    # if c['rwmc'] == '深度学习芯片设计-01班-双语' or c['dgjsmc']=='刘晓光':
    #     break
    # if no dup, put it into new json
    if not (chash in hash_list):
        hash_list.append(chash)
        op_json.append(c)

print([item for item, count in collections.Counter(hash_list_data).items() if count > 1])  # print duplicated course

with open('/Users/cyf/Documents/GitHub/sustc-course/course_remove_dup_json/2020-1.json', 'w') as f:
    json.dump(op_json, f, ensure_ascii=False)
