from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from os import makedirs
from os.path import exists
import logging
import json
import re

# Logger
logging.basicConfig(level=logging.INFO)

PATH_DATA_COURSE='data/courses/'

# SVG shape dictionary
icon_video = 'M5.562 4v10l6.875-5-6.875-5zm8.113 3.4a1.96 1.96 0 01.412 2.8 2.032 2.032 0 01-.412.4l-6.875 5c-.911.663-2.204.484-2.888-.4A1.96 1.96 0 013.5 14V4c0-1.105.923-2 2.062-2 .447 0 .881.14 1.238.4l6.875 5z'
icon_question = 'M6 6a1 1 0 110-2h10a1 1 0 010 2H6zm0 4a1 1 0 110-2h10a1 1 0 010 2H6zm0 4a1 1 0 010-2h10a1 1 0 010 2H6zM1 5a1 1 0 112 0 1 1 0 01-2 0zm0 4a1 1 0 112 0 1 1 0 01-2 0zm0 4a1 1 0 112 0 1 1 0 01-2 0z'
icon_exercise = 'M17.655 9.756l-4.946 4.95a1 1 0 11-1.415-1.415l4.29-4.294-4.277-4.293a.998.998 0 01.003-1.413 1 1 0 011.414.003l4.985 5.002a.998.998 0 01-.054 1.46zm-17.31 0a.998.998 0 01-.054-1.46l4.985-5.002a1 1 0 011.414-.003.998.998 0 01.003 1.413L2.416 8.997l4.29 4.294a1.002 1.002 0 01-1.415 1.416L.345 9.757z'

icon_type = {
    icon_video: 'Explanation',
    icon_question : 'Question',
    icon_exercise: 'Exercise',
}

def get_pagesource_course(url:str):
    """Get html course page
    """
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch()
            page = browser.new_page()
            page.goto(url)
            while page.is_visible('button:has-text("View chapter details")', timeout=5000):
                page.query_selector('button:has-text("View chapter details")').click()
                if not page.is_visible('button:has-text("View chapter details")', timeout=5000):
                    continue
            html = page.content()
            browser.close()
    except Exception as err:
        logging.error(str(err))
        html = None
    return html

def get_course(url:str):
    """Get course data
    """
    logging.debug("Preparing playwright...")
    html = get_pagesource_course(url)
    if html == None:
        logging.info("Pass " + url)
        pass
    else:
        logging.debug("Parse html...")
        html = BeautifulSoup(html, 'html.parser')
        course = html.find_all('li', {'class':'css-vurnku'})

        chapters = []
        for ch in course:
            title = ch.find('h3').text.strip()
            step = ch.find('span', {'class':'css-1slh6p0'}).text.strip()
            description = ch.find('p', {'class':'dc-chapter-block-description'}).text.strip()
            try:
                free = ch.find('strong', {'class':'css-1gzxid2'}).text.strip()
                if free == 'Free':
                    free = True
                else:
                    free = False
            except:
                free = False

            chapter_urls = ch.find('div', {'class':'css-1jg92yp'}).find_all('a', href=True)
            subchapter = []
            for a in chapter_urls:
                chap_title = a.find('span', {'class':'css-1rbq0za'}).text.strip()
                chap_type = a.find('div', {'class':'css-1nobm1w'}).find('path')['d']
                if chap_type in list(icon_type.keys()):
                    chap_type = icon_type[chap_type]
                else:
                    chap_type = 'Unknown'
                chap_xp = a.find('span', {'class':'css-4ldgir'}).text.replace('xp', '').strip()

                details = {
                    'name': chap_title,
                    'type': 'Sub-chapter',
                    'content_type': chap_type,
                    'reward': int(chap_xp),
                }
                subchapter.append(details)

            chapter = {
                'step': int(step),
                'name': title,
                'description': description,
                'type': 'Chapter',
                'free': free,
                'subchapter': subchapter,
            }
            chapters.append(chapter)

        chapters = sorted(chapters, key=lambda d: d['step']) 

        # Course details
        course_name = html.find('h1', {'data-cy':'course-title'}).text.strip()

        # Prerequisite
        prerequisite, track = None, None
        section_info = html.find('div', {'class':'css-5is1tl-CoursePage'})
        for div in section_info.find_all('div', {'class':'css-3r6l5t-CoursePage'}):
            if div.find('p').text.strip() == 'Prerequisites':
                list_a = div.find_all('a', href=True)
                prerequisite = []
                for a in list_a:
                    prereq_url = 'https://www.datacamp.com' + a['href']
                    prereq_name = a.text.strip()
                    prereq_item = {
                        'name': prereq_name,
                        'type': 'Course',
                        'url': prereq_url,
                    }
                    prerequisite.append(prereq_item)
            elif div.find('p').text.strip() == 'In the following tracks':
                list_a = div.find_all('a', href=True)
                track = []
                for a in list_a:
                    track_url = 'https://www.datacamp.com' + a['href']
                    track_name = a.text.strip()
                    track_item = {
                        'name': track_name,
                        'type': 'Track',
                        'url': track_url,
                    }
                    track.append(track_item)
            else:
                pass

        # Instructor
        section_instructor = html.find_all('div', {'class':'css-1qrdlp0-CoursePage'})
        if section_instructor == []:
            section_instructor = html.find_all('div', {'class':'css-1f254jt-CoursePage'})
        instructor = []
        for item in section_instructor:
            instructor_name = item.find('h4').text.strip()
            person = {
                'name': instructor_name,
                'type': 'Person',
                #'url': 'https://www.datacamp.com' + section_instructor.find('a', {'class':'css-1bda48x'}, href=True)['href'],
            }
            instructor.append(person)

        data = {
            'name': course_name,
            'type': 'Course',
            'prerequisite': prerequisite,
            'roadmap': track,
            'instructor': instructor,
            'chapter': chapters,
            'url': url,
        }

        return data


def scrape_course(url:str):
    """Scrape and save course data from datacamp.com/courses/slug-of-course
    """
    if not re.findall(r'^https?://(www.)?datacamp.com/courses/', url):
        logging.error('Incorrect url, example: https://www.datacamp.com/courses/introduction-to-data-engineering')
        pass
    else:
        data = get_course(url)
        if not exists(PATH_DATA_COURSE): makedirs(PATH_DATA_COURSE)
        filename = f"{PATH_DATA_COURSE}{url.replace('https://www.datacamp.com/courses/','')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logging.info("Data saved to " + filename)
