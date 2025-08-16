#!/usr/bin/env python3
"""
Download course catalog data for all terms from catalog.ustc.edu.cn
and import them using import_courses_catalog.py

Usage: python3 download_all_catalog.py <cookie>
"""

import sys
import os
import requests
import json
import subprocess
import time
import traceback
from pathlib import Path

# Change to script directory and add parent to path for imports
os.chdir(os.path.dirname(__file__))
sys.path.append('..')  # fix import directory

def validate_response(response, description):
    """Validate API response and handle errors"""
    try:
        response.raise_for_status()
        data = response.json()
        if not data:
            print(f"Warning: Empty response for {description}")
        return data
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error for {description}: {e}")
        print(f"Response content: {response.text[:500]}")
        raise
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response for {description}: {e}")
        print(f"Response content preview: {response.text[:500]}")
        raise
    except Exception as e:
        print(f"Unexpected error for {description}: {e}")
        raise

def download_with_retry(url, headers, description, max_retries=3):
    """Download with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"Downloading {description} (attempt {attempt + 1}/{max_retries})")
            response = requests.get(url, headers=headers, timeout=30)
            return validate_response(response, description)
        except KeyboardInterrupt:
            print("Download interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to download {description}: {e}")
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts, giving up")
                raise
            print("Retrying in 2 seconds...")
            time.sleep(2)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 download_all_catalog.py <cookie>")
        print("")
        print("How to obtain the cookie:")
        print("1. Visit https://catalog.ustc.edu.cn/query/lesson")
        print("2. Login with your USTC credentials")
        print("3. Open browser developer tools (F12)")
        print("4. Go to Network tab or Application tab -> Storage -> Cookies")
        print("5. Copy the entire cookie string for catalog.ustc.edu.cn")
        print("")
        print("Example:")
        print("python3 download_all_catalog.py '_ga_...; ustc_cas_auth=...'")
        sys.exit(1)

    cookie = sys.argv[1].strip()
    if cookie.startswith('cookie: '):
        cookie = cookie[len('cookie: '):].strip()

    # Create data directory
    data_folder = Path('../data/courses-catalog')
    data_folder.mkdir(parents=True, exist_ok=True)

    # Setup headers similar to the provided curl command
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'cookie': cookie,
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://catalog.ustc.edu.cn/query/lesson',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    }

    print("Downloading semester list...")
    
    # Download semester list
    semester_url = 'https://catalog.ustc.edu.cn/api/teach/semester/list'
    semesters = download_with_retry(semester_url, headers, "semester list")
    
    if not semesters:
        print("Error: No semesters found")
        sys.exit(1)
    
    print(f"Found {len(semesters)} semesters")
    
    # Sort semesters by start date in descending order (newest first)
    semesters.sort(key=lambda x: x['start'], reverse=True)
    print("Processing semesters in reverse chronological order (newest first)")
    
    # Save semester list
    semester_file = data_folder / 'semesters.json'
    with open(semester_file, 'w', encoding='utf-8') as f:
        json.dump(semesters, f, ensure_ascii=False, indent=2)
    print(f"Saved semester list to {semester_file}")
    
    # Process each semester
    success_count = 0
    total_count = len(semesters)
    
    for semester in semesters:
        semester_id = semester['id']
        semester_name = semester['nameZh']
        semester_code = semester['code']
        
        print(f"\n{'='*60}")
        print(f"Processing: {semester_name} (ID: {semester_id}, Code: {semester_code})")
        print(f"{'='*60}")
        
        # Create filename for this semester's course data
        safe_name = semester_name.replace('/', '-').replace(' ', '_')
        lesson_file = data_folder / f'{safe_name}_lessons.json'
        
        try:
            # Check if file already exists and is recent
            if lesson_file.exists():
                file_age = time.time() - lesson_file.stat().st_mtime
                if file_age < 86400:  # Less than 24 hours old
                    print(f"Using cached lesson data from {lesson_file}")
                    lessons = json.loads(lesson_file.read_text(encoding='utf-8'))
                else:
                    print(f"Cached file too old, re-downloading...")
                    lessons = None
            else:
                lessons = None
            
            # Download lesson data if not cached
            if lessons is None:
                lesson_url = f'https://catalog.ustc.edu.cn/api/teach/lesson/list-for-teach/{semester_id}'
                lessons = download_with_retry(lesson_url, headers, f"lessons for {semester_name}")
                
                # Save lesson data
                with open(lesson_file, 'w', encoding='utf-8') as f:
                    json.dump(lessons, f, ensure_ascii=False, indent=2)
                print(f"Saved lesson data to {lesson_file}")
                
                # Add a small delay to avoid overwhelming the server
                time.sleep(1)
            
            print(f"Found {len(lessons)} courses for {semester_name}")
            
            # Call import_courses_catalog.py
            print(f"Importing {semester_name} into database...")
            
            import_cmd = [
                'python3', 
                'import_courses_catalog.py',
                '--id', str(semester_id),
                '--semester', str(semester_file),
                '--lesson', str(lesson_file),
                '--yes'  # Non-interactive mode
            ]
            
            # Ensure we're in the correct directory and import script exists
            if not os.path.exists('import_courses_catalog.py'):
                print("Error: import_courses_catalog.py not found in current directory")
                print(f"Current directory: {os.getcwd()}")
                sys.exit(1)
            
            result = subprocess.run(import_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Successfully imported {semester_name}")
                success_count += 1
            else:
                print(f"❌ Failed to import {semester_name}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
                # Ask user if they want to continue
                response = input(f"Continue with remaining semesters? [y/N] ")
                if response.lower() != 'y':
                    break
                    
        except KeyboardInterrupt:
            print("\nOperation interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error processing {semester_name}: {e}")
            print("Traceback:")
            traceback.print_exc()
            
            # Ask user if they want to continue
            response = input(f"Continue with remaining semesters? [y/N] ")
            if response.lower() != 'y':
                break
    
    print(f"\n{'='*60}")
    print(f"Import complete: {success_count}/{total_count} semesters imported successfully")
    print(f"{'='*60}")
    
    if success_count < total_count:
        print("Some imports failed. Check the output above for details.")
        sys.exit(1)
    else:
        print("All semesters imported successfully!")

if __name__ == "__main__":
    main()
