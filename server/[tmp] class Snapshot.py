
# METHODS AND CLASSES SHARED BETWEEN CLIENT AND SERVER


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

    def __init__(self, paths=None):
    # if restoring the server
        if paths:
            self.last_change, self.files = self.istant_snapshot(paths)
            return

    # else if I'm creating a new Snapshot
        self.last_change = time.time()
        self.files = {}         # md5 : [list of client_paths]

    def push(self, client_path):
        md5 = to_md5(client_path)
        if md5:
            if md5 in self.files:
                self.files[md5].append(client_path)
            else:
                self.files[md5] = [client_path]
        return md5

    def rm(self, md5, client_path):
        self.files[md5].pop(client_path)
        if not self.files[md5]:
            del self.files[md5]
