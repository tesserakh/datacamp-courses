from scraper import course, track, storage
from os import listdir
from os.path import exists
import logging
import json

logging.basicConfig(level=logging.INFO)

def crawl_track():
    """Crawl track data"""
    if not exists(storage.PATH_TRACK_LIST): track.scrape_track_list()
    with open(storage.PATH_TRACK_LIST, 'r') as f:
        data = json.load(f)
        urls = [track['url'] for track in data]

    for url in urls:
        try:
            track.scrape_track(url)
        except Exception as err:
            logging.error(f"Failed {url}: {str(err)}")


def get_url_from_track():
    """Import listed course urls from track data"""
    datapath = 'data/tracks/'
    urls = []
    for file in listdir(datapath):
        if file.endswith('.json'):
            filename = datapath + file
            with open(filename, 'r') as f:
                data = json.load(f)
                track = data['track']
                for item in track:
                    if item['type'] == 'Course':
                        if item['url'] not in urls:
                            urls.append(item['url'])
    return urls

def get_url_from_course():
    """Generate new course urls from scraped course data"""
    urls, reverse_urls, new_urls = [], [], []

    for file in listdir(storage.PATH_DATA_COURSE):
        if file.endswith('.json'):
            filename = storage.PATH_DATA_COURSE + file
            with open(filename, 'r') as f:
                data = json.load(f)
                urls.append(data['url'])
                if data['prerequisite'] != None:
                    for item in data['prerequisite']:
                        if item['url'] not in reverse_urls:
                            reverse_urls.append(item['url'])
    for url in reverse_urls:
        if url not in urls:
            new_urls.append(url)
    return new_urls

def get_course_data_from(what:str):
    """Retrieve course data from available stored urls"""
    # Import urls from course or track data
    if what == 'course':
        urls = get_url_from_course()
    elif what == 'track':
        urls = get_url_from_track()
    else:
        raise Exception("Invalid input, what='track' or what='course'")
    
    logging.info("Course url count: " + str(len(urls)))

    # Scrape course data
    for url in urls:
        try:
            course.scrape_course(url)
        except Exception as err:
            logging.error(f"Failed {url}: {str(err)}")


if __name__ == '__main__':
    crawl_track()
    get_course_data_from('track')
    get_course_data_from('course')
    get_course_data_from('course')
