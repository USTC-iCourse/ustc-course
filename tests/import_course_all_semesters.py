#!/usr/bin/env python3
import sys
import os
import requests
import lxml.html
import subprocess
import time
import datetime
import traceback

os.chdir(os.path.dirname(__file__))
sys.path.append('..')  # fix import directory

if len(sys.argv) != 2:
    print('Usage: ' + sys.argv[0] + ' <cookie for jw.ustc.edu.cn>')
    sys.exit(1)
cookie = sys.argv[1]
if cookie.startswith('cookie: '):
    cookie = cookie[len('cookie:'):].strip()

folder = '../data/courses-jw.ustc'
if not os.path.exists(folder):
    os.makedirs(folder)

headers = {
    'cookie': cookie,
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
    'authority': 'jw.ustc.edu.cn'
}

# get user ID
program_url = 'https://jw.ustc.edu.cn/for-std/course-select'
# will redirect to /for-std/course-select/turns/<int:user_id>
r = requests.get(program_url, headers=headers)
if len(r.history) < 2:
    print('Failed to get user ID from program redirect: no redirect found')
    sys.exit(1)
redirect_url = r.history[1].url
user_id = redirect_url.split('/')[-1]
if not user_id.isnumeric():
    print('Failed to get user ID from program redirect: user ID is not numeric')
    sys.exit(1)
print('User ID: ' + user_id)
headers['referer'] = 'https://jw.ustc.edu.cn/for-std/lesson-search/index/' + user_id

# fetch all semesters
index_url = 'https://jw.ustc.edu.cn/for-std/lesson-search/index/' + user_id
r = requests.get(index_url, headers=headers)
doc = lxml.html.fromstring(r.text)
options = doc.xpath('//select[@id="semester"]/option')
if len(options) == 0:
    print('Semesters not found, please check whether cookie is valid')
    sys.exit(1)


def need_download(filepath):
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        return True
    mtime = os.path.getmtime(filepath)
    mtime_obj = datetime.datetime.fromtimestamp(mtime)
    return datetime.datetime.now() - datetime.timedelta(days=1) > mtime_obj

print('Found ' + str(len(options)) + ' semesters')
for option in options:
    semester_id = option.attrib['value']
    semester_name = option.text
    echo_text = 'semester ' + semester_name + ' (ID=' + semester_id + ')'

    save_file_path = os.path.join(folder, semester_name + '.json')
    if need_download(save_file_path):
        print('Downloading ' + echo_text)
        lesson_url = 'https://jw.ustc.edu.cn/for-std/lesson-search/semester/' + semester_id + '/search/' + user_id + '?courseCodeLike=&codeLike=&educationAssoc=&courseNameZhLike=&teacherNameLike=&schedulePlace=&classCodeLike=&courseTypeAssoc=&classTypeAssoc=&campusAssoc=&teachLangAssoc=&roomTypeAssoc=&examModeAssoc=&requiredPeriodInfo.totalGte=&requiredPeriodInfo.totalLte=&requiredPeriodInfo.weeksGte=&requiredPeriodInfo.weeksLte=&requiredPeriodInfo.periodsPerWeekGte=&requiredPeriodInfo.periodsPerWeekLte=&limitCountGte=&limitCountLte=&majorAssoc=&majorDirectionAssoc=&queryPage__=1%2C100000&_=1656750360507'
        for repeat in range(5):
            try:
                r = requests.get(lesson_url, headers=headers)
                r.raise_for_status()  # Raise exception for bad status codes
                break
            except KeyboardInterrupt:
                sys.exit(1)
            except Exception as e:
                print('Failed to download ' + echo_text + ', retry...')
                print('Error details:', str(e))
                print('Traceback:')
                traceback.print_exc()
                if repeat == 4:  # Last retry
                    print('Failed to download ' + echo_text + ' after 5 attempts, giving up.')
                    sys.exit(1)
                continue
        # Validate response content before saving
        try:
            import json
            json.loads(r.text)  # Validate JSON
        except json.JSONDecodeError as e:
            print('Failed to download ' + echo_text + ': Server response is not valid JSON')
            print('JSON decode error:', str(e))
            print('Response content preview (first 500 chars):')
            print(repr(r.text[:500]))
            sys.exit(1)
        except Exception as e:
            print('Failed to validate response for ' + echo_text + ':', str(e))
            sys.exit(1)
        
        with open(save_file_path, 'w') as f:
            f.write(r.text)
    else:
        print('Using cached ' + echo_text)

    print('Download complete, importing ' + echo_text)
    subprocess.run(['python3', 'import_courses_new.py', save_file_path])
    print('Import ' + echo_text + ' complete')

