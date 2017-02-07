import os
import sys
import time
from collections import defaultdict

import urllib.request
from urllib.parse import quote

from bs4 import BeautifulSoup

from mutagen.easyid3 import EasyID3

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QByteArray

def get_mp3_file_paths(paths):
    file_paths = []
    for p in paths:
        if not os.path.isdir(p):
            _, ext = os.path.splitext(p)
            if ext == '.mp3':
                file_paths.append(p)
            continue

        in_dir_paths = [os.path.join(p, name) for name in os.listdir(p)]
        file_paths.extend(get_mp3_file_paths(in_dir_paths))

    return file_paths


def get_artist_album_dict(mp3_file_paths):
    artist_album_dict = defaultdict(set)
    for p in mp3_file_paths:
        try:
            tag = EasyID3(p)
        except:
            print('mp3 load error: {}'.format(p))
            continue
        artist_name = tag['artist'][0]
        album_name = tag['album'][0]
        dirname = os.path.dirname(p)
        artist_album_dict[artist_name].add((album_name, dirname))
    return artist_album_dict


def get_n_albums(artist_album_dict):
    n_albums = 0
    for val in artist_album_dict.values():
        n_albums += len(val)
    return n_albums
       
    
def download_cover_images(artist_name, album_name, start_index, n_query):
    t0 = time.time()
    
    query = urllib.parse.quote_plus('{}+{}'.format(artist_name, album_name), encoding='utf-8')
    query_url = 'http://image.search.yahoo.co.jp/search?p={}&b={}&dim=medium'.format(query, start_index)

    response = urllib.request.urlopen(query_url)
    data = response.read().decode('utf-8')

    soup = BeautifulSoup(data, 'lxml')
    a_tags = soup.find_all('a')
    IMAGE_EXTENTIONS = ['.jpg', '.jpeg', '.png']
    image_urls = []
    for a_tag in a_tags:
        link_url = a_tag.get('href')
        for ext in IMAGE_EXTENTIONS:
            if ext in link_url:
                image_urls.append(link_url)
    
    pixmaps = []
    for url in image_urls:
        pixmap = generate_pixmap(url)
        if pixmap is not None:
            pixmaps.append(pixmap)
        if len(pixmaps) >= n_query:
            print('elapsed: {}'.format(time.time() - t0))
            return pixmaps[:n_query]
    else:
        pixmaps += download_cover_images(artist_name, album_name,
                                         start_index + len(pixmaps),
                                         n_query - len(pixmaps))
        return pixmaps[:n_query]
        
def generate_pixmap(url):
    try:
        image_data = urllib.request.urlopen(url)
    except:
        return None
        
    byte_data = QByteArray(image_data.read())
    image_data.close()

    _, ext = os.path.splitext(url.split('/')[-1])
    pixmap = QPixmap()
    try:
        pixmap.loadFromData(byte_data, ext[1:])
    except:
        return None

    return pixmap