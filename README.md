YATS
====

[![license](https://img.shields.io/github/license/mediafactory/yats.svg)]()
[![GitHub issues](https://img.shields.io/github/issues/mediafactory/yats.svg)]()
[![GitHub pull requests](https://img.shields.io/github/issues-pr/mediafactory/yats.svg)]()
[![GitHub contributors](https://img.shields.io/github/contributors/mediafactory/yats.svg)]()
[![GitHub forks](https://img.shields.io/github/forks/mediafactory/yats.svg?style=social&label=Fork)]()
[![GitHub stars](https://img.shields.io/github/stars/mediafactory/yats.svg?style=social&label=Stars)]()

- yet another (trouble) ticketing system based on Python Django
- &copy; media factory, Lübeck, Germany http://www.mediafactory.de
- requires: Django 1.11.x (Python 2.x)
- See also: YATSE (https://github.com/mediafactory/yatse)

DEMO
-----
https://yats.mediafactory.de

Staff User:  
Login: staff.user  
Password: qwertz  

Customer User:  
Login: customer.user  
Password: qwertz  

Or use vagrant!  

VAGRANT
-----
howto:
```
$ cd vagrant
$ vagrant up
```
Wait! :-)
Point your browser at:
http://192.168.33.11
or for admin interface:
http://192.168.33.11/admin

Staff User:  
Login: admin  
Password: admin  

WHY JUST ANOTHER?
-----
We used to use TRAC for a long time and were quiet happy. But every time, we wanted to customize it, it took us a long to rethink the way, trac was developed or find a plugin working with our version.  
Today all our web projects are build on top of django. So it is much easier to change YATS and we are faster in adding new feateures. We think, we kept it simple in the backend, so it is still easy to modifie for people not familiar with the YATS source (as long as you know django).

KEY FEATURES
-----
- custom fields (mandatory fields and default values configurable)
- different view of tickets for customers - fields hideable from customers (even in emails)
- mails for ticket changes, comments, close, reopen, reassign
- searchable fields configurable
- searches saveable as reports
- ticket history
- ticket references (including back references)
- complex workflows
- multiple kanban boards with columns saved from searches
- file attachments with drag/drop (optionally virus scanned)
- twitter bootstrapp 2 - responsive layout
- git TAGS from Github as versions example
- XML-RPC API
- compatible with tracker (see https://github.com/mediafactory/tracker)
- simple, but yet powerful! No real magic :-) 2 sourcefiles besides the django stuff (tickets.py and shortcuts.py)
- SSO (single sign on), if you are using multiple YATS and YATSE (but you or your customers can still login locally)
- Simple-Mode for using YATS as a simple task manager

INSTALLATION
-----
no pypi package yet!

needs:  
pil or pillow  
rpc4django  
diff-match-patch  
http://nodebox.net/code/index.php/Graph  
httplib2 (if using tags from github)    
django-wiki (not yet used)  

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

./manage.py migrate  

ALTERNATIVE PACKAGES
-----
https://www.djangopackages.com/grids/g/ticketing/
