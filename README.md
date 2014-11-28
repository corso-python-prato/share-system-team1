RawBox
==================
[![Build Status](https://api.travis-ci.org/corso-python-prato/share-system-team1.svg)](https://travis-ci.org/corso-python-prato/share-system-team1)
[![Coverage Status](https://img.shields.io/coveralls/corso-python-prato/share-system-team1.svg)](https://coveralls.io/r/corso-python-prato/share-system-team1)

## How to make a first testing setup
- **Clone the repository**
```
    git clone git@github.com:corso-python-prato/share-system-team1.git rawbox
```
or
```
    git clone https://github.com/corso-python-prato/share-system-team1.git rawbox
```

- **Create two virtualenvs**: one for the server, one for the client. Install dependencies for each one  
Open a shell (start every shell from the path of downloaded repository) and write:
```
    virtualenv server_rb
    source server_rb/bin/activate
    pip install -r rawbox/server/requirements.txt
```
In a new shell, write:
```
    virtualenv client_rb
    source client_rb/bin/activate
    pip install -r rawbox/client/requirements.txt
```
- **Set email configuration**  
Create a file rawbox/server/email_settings.ini (there is an
example) and fill it with your email server settings. We are using mailgun,
for example.

- **Run the server**  
on the server shell, type:
```
    python rawbox/server/server.py
```
- **Run the client daemon**  
on the client shell, type:
```
    cd rawbox/client
    python client_daemon.py
```
- Open a new shell and **run the command manager**:
```
    source client_rb/bin/activate
    cd rawbox/client
    python client_cmdmanager.py
```
- **Now you can make your tests!**  
 

The next time, you'll have only to open the virtualenvs:  
shell 1:
```
    source server_rb/bin/activate
    python rawbox/server/server.py
```
shell 2:
```
    source client_rb/bin/activate
    cd rawbox/client
    python client_daemon.py
```
shell 3:
```
    source client_rb/bin/activate
    cd rawbox/client
    pyton client_cmdmanager.py
```


<h2>More info</h2>    
[Visit the Website](http://marcopretelliprove.altervista.org/RawBox/) (WORK IN PROGRESS)

<h2>Internal implementation</h2>
Deamon Client
    
![alt tag](http://marcopretelliprove.altervista.org/img/daemonscheme.png)

CMD Manager Client

![alt tag](http://marcopretelliprove.altervista.org/img/cmdmanager.png)
