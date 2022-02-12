import json
import collections

# Opening JSON file
f = open('course-2021-spring.json')

# returns JSON object as
# a dictionary
data = json.load(f)

# unique = { each['kcdm'] : each for each in data }.values()
# unique_teacher = { each['dgjsmc'] : each for each in unique }.values()
hash_list = []
hash_list_data = []
op_json = []
for c in data:
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

print([item for item, count in collections.Counter(hash_list_data).items() if count > 1])

with open('remove_dup.json', 'w') as f:
    json.dump(op_json, f, ensure_ascii=False)
