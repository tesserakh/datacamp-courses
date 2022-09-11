from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from scraper import storage
from os import makedirs
from os.path import exists
import logging
import json
import re


# Logger
logging.basicConfig(level=logging.INFO)

# Functions
def get_pagesource_track_list(url:str):
    """Get html page of track list to be parsed
    """
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch()
            page = browser.new_page()
            page.goto(url)
            if page.is_visible('.css-1h8jdu0-TrackList', timeout=3000):
                page.wait_for_timeout(3000)
                html = page.content()
            browser.close()
    except Exception as err:
        logging.error(str(err))
        html = None
    return html

def get_pagesource_track(url:str):
    """Get html page of track to be parsed
    """
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch()
            page = browser.new_page()
            page.goto(url)
            while page.is_visible('button:has-text("See All")', timeout=5000):
                page.query_selector('button:has-text("See All")').click()
                if not page.is_visible('button:has-text("See All")', timeout=5000):
                    continue
            html = page.content()
            browser.close()
    except Exception as err:
        logging.error(str(err))
        html = None
    return html

def parse_track_list(html):
    """Parse track list html page
    """
    html = BeautifulSoup(html, 'html.parser')
    track_list = html.find_all('a', {'class':'css-y0hih7-ContentCard'}, href=True)
    data = []
    for a in track_list:
        details = a.find('div', {'class':'css-1ujh897-TrackCard'})
        details = [item.text.strip() for item in details.find_all('span', {'class':'css-1rbq0za'})]
        track = {
            'name': a.find('h3').text.strip(),
            'description': a.find('p').text.strip(),
            'type': 'Track',
            'category': a.find('svg').find('title').text.strip(),
            'duration': details[0],
            'course_count': int(details[1].replace('courses', '').strip()),
            'url': 'https://www.datacamp.com' + a['href'],
        }
        data.append(track)
    return data

def parse_track(html):
    """Parse track html page
    """
    html = BeautifulSoup(html, 'html.parser')
    header = html.find('header')
    track_name = header.find('h1', {'data-cy':'track-title'}).text.strip()
    track_description = header.find('p', {'class':'css-14idxgz-TracksPage'}).text.strip()
    track_category = header.find('span', {'class':'css-1g6a7hg-TracksPage'}).text.strip()
    # Parse course brief
    section = html.find('section', {'class':'css-e3d8dw-TracksPage'})
    step = [circle.text.strip() for circle in section.find_all('div', {'class':'css-54nx8s-TrackContentCard'})]
    track, count = [], 0
    for a in section.find_all('a', {'class':'css-duaogc-TrackContentCard'}, href=True):
        course_url = a['href']
        course_name = a.find('strong', {'class':'css-1dbp6pz-TrackContentCard'}).text.strip()
        course_category = a.find('svg', {'class':'css-gwz4il-TrackContentCard'}).find('title').text.strip()
        if re.findall('signal', course_url):
            course_type = 'Milestone'
        elif re.findall('courses', course_url):
            course_type = 'Course'
        elif re.findall('projects', course_url):
            course_type = 'Project'
        else:
            course_type = 'Unknown'
            logging.debug(f"New type of track {track_name} ({'https://www.datacamp.com' + course_url})")
        if course_type == 'Course' or course_type == 'Project':
            description = a.find('p', {'class':'css-r9ojyg-TrackContentCard'}).text.strip()
            duration = a.find('p', {'class', 'css-1jr04uj-TrackContentCard'}).text.strip()
            instructor_name = a.find('footer').find('p', {'class':'css-v0xch9-TrackContentCard'}).text.strip()
            instructor_title = a.find('footer').find('p', {'class':'css-1rbq0za'}).text.strip()
            course = {
                'step': int(step[count]),
                'name': course_name,
                'description': description,
                'type': course_type,
                'category': course_category,
                'duration': duration,
                'instructor': {'name': instructor_name, 'title': instructor_title},
                'url': 'https://www.datacamp.com' + course_url,
            }
            track.append(course)
        else:
            course = {
                'step': int(step[count]),
                'name': course_name,
                'type': course_type,
                'category': course_category,
                'url': 'https://www.datacamp.com' + course_url,
            }
            track.append(course)
        count += 1

    data = {
        'name': track_name,
        'description': track_description,
        'type': 'Track',
        'category': track_category,
        'track': track,
    }
    return data


def scrape_track_list():
    """Scrape and save list of tracks from datacamp.com/tracks/career
    """
    url = 'https://www.datacamp.com/tracks/career'
    logging.info("Get track list from " + url)
    html = get_pagesource_track_list(url)
    data = parse_track_list(html)
    if not exists(storage.PATH_DATA): makedirs(storage.PATH_DATA)
    with open(storage.PATH_TRACK_LIST, 'w') as f:
        json.dump(data, f, indent=2)
    logging.info("Data saved to " + storage.PATH_TRACK_LIST)

def scrape_track(url:str):
    """Scrape and save track data from datacamp.com/tracks/slug-of-track
    """
    if not re.findall(r'^https?://(www.)?datacamp.com/tracks/', url):
        logging.error('Incorrect url, example: https://www.datacamp.com/tracks/r-programmer')
        pass
    else:
        html = get_pagesource_track(url)
        if html == None:
            logging.error("Failed to retrieve html: " + url)
            pass
        else:
            data = parse_track(html)
            data.update({'url': url})
            if not exists(storage.PATH_DATA_TRACK): makedirs(storage.PATH_DATA_TRACK)
            filename = f"{storage.PATH_DATA_TRACK}{url.replace('https://www.datacamp.com/tracks/','')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info("Data saved to " + filename)
