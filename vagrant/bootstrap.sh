#!/usr/bin/env bash

# debian packages
apt-get update
#apt-get upgrade
apt-get install -y memcached python-memcache python-httplib2 locales-all python-pyclamd python-imaging libjpeg8 libjpeg-dev libpng-dev screen python-pip apache2 apache2-mpm-prefork libapache2-mod-wsgi

# python modules
sites=`python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()"`
ln -fs /vagrant_modules/django $sites 2>/dev/null
ln -fs /vagrant_modules/yats $sites 2>/dev/null
ln -fs /vagrant_modules/south $sites 2>/dev/null
ln -fs /vagrant_modules/bootstrap_toolkit $sites 2>/dev/null
ln -fs /vagrant_modules/rpc4django $sites 2>/dev/null
ln -fs /vagrant_modules/graph $sites 2>/dev/null
ln -fs /vagrant_modules/wiki $sites 2>/dev/null

pip install -r /vagrant/requirements.txt

# clamav config
ret=`grep -ir "TCPSocket" /etc/clamav/clamd.conf`
if [ "" = "$ret" ]; then
echo "TCPSocket 3310" >> /etc/clamav/clamd.conf
fi
ret=`grep -ir "TCPAddr" /etc/clamav/clamd.conf`
if [ "" = "$ret" ]; then
echo "TCPAddr 127.0.0.1" >> /etc/clamav/clamd.conf
fi
freshclam&

# yats web
mkdir -p /var/web/yats
ln -fs /vagrant_sites/static /var/web/yats/static
ln -fs /vagrant_sites/web /var/web/yats/web

mkdir -p /var/web/yats/files
chown root:vagrant /var/web/yats/files
chmod go+w /var/web/yats/files

mkdir -p /var/web/yats/logs
touch /var/web/yats/logs/django_request.log
chown root:vagrant /var/web/yats/logs/django_request.log
chmod go+w /var/web/yats/logs/django_request.log

# yats config
mkdir -p /usr/local/yats/config
ln -fs /vagrant/web.ini /usr/local/yats/config/web.ini

# yats db
mkdir -p /var/web/yats/db
chown root:vagrant /var/web/yats/db
chmod go+w /var/web/yats/db

cd /var/web/yats/web/
python manage.py syncdb --noinput
python manage.py migrate
python manage.py loaddata /vagrant/init_db.json

# apache config
cp /vagrant/yats.apache /etc/apache2/sites-available/yats
a2dissite default
a2ensite yats
apache2ctl restart

# deb upgrade
apt-get -y upgrade &