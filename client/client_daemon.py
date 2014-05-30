#!/usr/bin/env python
#-*- coding: utf-8 -*-


#inotify observer unable to detect 'dragging file to trash' events
#from https://github.com/gorakhargosh/watchdog/issues/46 use polling solution

#from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import time
import requests

SERVER_URL = 'http://127.0.0.1:5000/API/v1/'
PATH = '/home/user/Documents/MyDir'

class DirectoryEvent(FileSystemEventHandler):
    def on_any_event(self, event):
        request = requests.get(SERVER_URL)
        
def main():
    event_handler = DirectoryEvent()
    observer = Observer()
    observer.schedule(event_handler, PATH, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()