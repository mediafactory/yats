YATS
====

yet another ticket system base on Python Django

DEMO
-----
http://yats.mediafactory.de

Staff User:  
Login: staff.user  
Password: qwertz  

Customer User:  
Login: customer.user  
Password: qwertz  

INSTALLATION
-----
no pypi package yet!

needs:  
pil or pillow  
httplib2 (if using tags from github)  

should need:  
pyclamd (add TCPSocket 3310 and TCPAddr 127.0.0.1 to its config and restart)  
memcache  

There is a debian package which includes parts of all, but is very special designed for our usecase as we make no use of pip. It distributes all packages not available via debian packages.

settings.py reads part of its config data from an inifile (see top of settings.py).

The project is splited into 2 parts:
- the app (yats)
- the web, using the app (web)

Customization is done in the web module - e.g. add more ticket fields (models.py in web) besides the settings itself (settings.py and ini file).
So far the app needs 2 folders (for logging and attachments as defined in the inifile). Make sure the webserver has write access to those folders.
