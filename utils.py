import os
import sys
import time
from collections import defaultdict

import threading
from queue import Queue

import requests
from bs4 import BeautifulSoup

from mutagen.easyid3 import EasyID3

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QByteArray


N_THREADS = 4


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
    
    query = '{}+{}'.format(artist_name, album_name)
    query_params = {'p': query, 'b': start_index, 'dim': 'medium'}
    search_url = 'http://image.search.yahoo.co.jp/search'
    response = requests.get(search_url, params=query_params)
    data = response.text

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
    for i in range(0, len(image_urls), n_query):        
        tmp_pixmaps = generate_pixmap(image_urls[i:(i + n_query)])
        for tmp in tmp_pixmaps:
            if tmp is not None:
                pixmaps.append(tmp)
        if len(pixmaps) >= n_query:
            print('elapsed: {}'.format(time.time() - t0))
            return pixmaps[:n_query]
    else:
        pixmaps += download_cover_images(artist_name, album_name,
                                         start_index + len(pixmaps),
                                         n_query - len(pixmaps))
        return pixmaps[:n_query]
    
    
def generate_pixmap_parallel(data_queue, results_list):
    while not data_queue.empty():
        url, index = data_queue.get()
        try:
            response = requests.get(url, stream=True)
        except:
            results_list[index] = None
            data_queue.task_done()
            continue
            
        byte_data = QByteArray(response.raw.read())
        response.close()
    
        _, ext = os.path.splitext(url.split('/')[-1])
        pixmap = QPixmap()
        try:
            pixmap.loadFromData(byte_data, ext[1:])
        except:
            results_list[index] = None
            data_queue.task_done()
            continue
    
        results_list[index] = pixmap        
        data_queue.task_done()
        
        
def generate_pixmap(urls):
    results = [0 for i in range(len(urls))]
    data_queue = Queue()
    for i in range(len(results)):
        data_queue.put((urls[i], i))
    
    workers = []    
    for i in range(N_THREADS):
        worker = threading.Thread(target=generate_pixmap_parallel, args=(data_queue, results))
        worker.setDaemon(True)
        worker.start()
        workers.append(worker)
     
    data_queue.join()
    for w in workers:
        w.join()
        
    return results