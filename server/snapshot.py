#!/usr/bin/env python
#-*- coding: utf-8 -*-


def to_md5(path, block_size=2**20):
    ''' if path is a file, return a md5;
    if path is a directory, return False'''
    if os.path.isdir(path):
        return False

    m = hashlib.md5()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(block_size), b''): 
            m.update(chunk)

    return m.digest()


class Snapshot(object):
    def __init__(self, timestamp=None, files=None):
    # if restoring
        if timestamp and files:
            self.last_change = timestamp
            self.files = files
            return

    # else if I'm creating a Snapshot for a new user
        self.last_change = time.time()
        self.files = {}         # { md5 : [list of client_paths] }


    def istant_snapshot(self, paths):
        # TODO
        pass


    def to_json(self):
        # TODO
        pass


# second constructor
    @classmethod
    def from_JSON(cls, file_path):
        try:
            f = open(file_path, "r")
            data = json.load(ud)
            f.close()
        except IOError:         # missing file
            pass                  # TODO
        except ValueError:      # invalid json
            pass                  # TODO
        else:
            return cls(timestamp=data["last_change"], files=data["files"])


    @classmethod
    def restore_server(cls, paths):
        files = self.istant_snapshot(paths)
        # TODO: find the most recent update in file stamps.
        return cls(timestamp=last_change, files=files)
        

    def push(self, client_path):
        md5 = to_md5(client_path)
        if md5:
            if md5 in self.files:
                self.files[md5].append(client_path)
            else:
                self.files[md5] = [client_path]
            self.last_change = time.time()
        return md5

    def rm(self, md5, client_path):
        self.files[md5].pop(client_path)
        if not self.files[md5]:
            del self.files[md5]
        self.last_change = time.time()
