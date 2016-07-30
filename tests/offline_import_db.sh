#!/bin/bash
ssh -t moocwiki 'mysqldump -u root -p icourse | gzip >icourse.sql.gz'
scp moocwiki:icourse.sql.gz .
gunzip icourse.sql.gz
mysql -u root -p icourse <icourse.sql
./import_db.py
mysqldump -u root -p icourse | gzip >icourse-new.sql.gz
scp icourse-new.sql.gz moocwiki:
ssh moocwiki gunzip icourse-new.sql.gz
#ssh -t moocwiki 'mysql -u root -p icourse <icourse-new.sql'
