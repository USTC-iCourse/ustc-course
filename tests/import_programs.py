#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *
from datetime import datetime
import json
import requests

# configuration for information source
domain = 'catalog.ustc.edu.cn'
site_root = 'https://' + domain + '/'

headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
    'authority': domain,
    'referer': site_root + 'plan'
}

# get access token
token_json = requests.get(site_root + 'get_token', headers=headers)
access_token = json.loads(token_json.text)['access_token']

# load existing data
existing_majors = Major.query.all()
majors_map = { major.code : major for major in existing_majors }

existing_programs = Program.query.all()
programs_map = { program.id : program for program in existing_programs }

def load_tree():
    tree_json = requests.get(site_root + 'api/teach/program/tree?access_token=' + access_token, headers=headers)
    tree = json.loads(tree_json.text)
    
    for dept_id in tree:
        dept_data = tree[dept_id]
        dept_code = dept_data['code']
        for major_id in dept_data['majors']:
            major_data = dept_data['majors'][major_id]
            major_code = major_data['code']
    
            major = majors_map[major_code] if major_code in majors_map else Major()
            major.code = major_code
            major.name = major_data['nameZh']
            major.name_en = major_data['nameEn']
            db.session.add(major)
    
            programs = major_data['programs']
            for program_data in programs:
                program_id = program_data['id']
                program = programs_map[program_id] if program_id in programs_map else Program()
                program.id = program_id
                program.name = program_data['nameZh']
                program.name_en = program_data['nameEn']
                program.grade = program_data['grade']
                program.train_type = program_data['trainType']
                db.session.add(program)


load_tree()
db.session.commit()
