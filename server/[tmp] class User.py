

# manteinig two dictionaries:
# paths     => { client_path : [server_path, md5] }
# snapshot  => { md5 : [client_path1, client_path2] }
# server_path is for shared directories management

class User(object):
# class initialization: try with config, else from scratch
    users = {}
    counter_id = 0

    try:
        ud = open(USERS_DATA, "r")
        saved = json.load(ud)
        ud.close()
    # if error, create new structure from scratch
    except IOError:
        pass                # missing file
    except ValueError:      # invalid json
        os.remove(USERS_DATA)
    else:
        counter_id = saved["counter_id"]
        for u, v in saved["users"].items():
            User(u, u["psw"], u["paths"])


# other class and static methods
    @classmethod
    def get_new_id(cls):
        new_id = hex(cls.counter_id)[2:]
        cls.counter_id += 1    
        return new_id


    @classmethod
    def save_users(cls, filename=None):
        if not filename:
            filename = USERS_DATA

        to_save = {
            "counter_id" : cls.counter_id,
            "users" : {}
        }        
        for u, v in users.items():
            to_save["users"][u] = v.to_dict()

        with open(filename, "w") as f:
            json.dump(to_save, f)


# dynamic methods
    def __init__(self, username, password, paths=None):
    # if restoring the server
        if paths:
            self.psw = password
            self.paths = paths
            self.snapshot = Snapshot(paths)
            User.user[username] = self
            return

    # else if I'm creating a new user
        if username in User.users:
            return "This user already exists", 409

        psw_hash = sha256_crypt.encrypt(password)
        dir_id = User.get_new_id()
        full_path = os.path.join(USERS_DIRECTORIES, dir_id)
        try:
            os.mkdir(full_path)
        except OSError:
            raise ConflictError(
                    "Conflict while creating the directory for a new user"
            )

        self.psw = psw_hash
        self.paths = {          # path of each file and directory of the user!
            # client_path : [server_path, md5]
            "" : [full_path, False]
        }
        self.snapshot = Snapshot()

        User.users[username] = self
        User.save_users()

        return "User created!", 201


    def to_dict(self):
        return {
            "psw" : self.psw,
            "paths" : self.paths
        }


    def push_path(self, client_path):
        md5 = self.snapshot.push(client_path)
        if client_path in self.paths:
            self.paths[client_path][1] = md5        # update md5 value
        else:
            user_directory = self.paths[""]
            server_path = os.path.join(user_directory, client_path)
            # TODO: manage shared folder here. Something like:
            # for s, v in shared_folder.items():
            #     if server_path.startswith(s):
            #         update every user
            self.paths[client_path] = [server_path, md5]


    def rm_path(self, client_path):
        md5 = self.paths[client_path][1]
        self.snapshot.rm(md5, client_path)
        del self.paths[client_path]
