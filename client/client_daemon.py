#!/usr/bin/env python
#-*- coding: utf-8 -*-


# inotify observer unable to detect 'dragging file to trash' events
# from https://github.com/gorakhargosh/watchdog/issues/46 use polling solution

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import time
import requests
import json


def load_config():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    return config


class DirectoryEventHandler(FileSystemEventHandler):

    def __init__(self, server_url):
        self.server_url = server_url

    def on_any_event(self, event):
        request = requests.get(self.server_url)


def main():
    config = load_config()
    event_handler = DirectoryEventHandler(config['server_url'])
    observer = Observer()
    observer.schedule(event_handler, config['dir_path'], recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
