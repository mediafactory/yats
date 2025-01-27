#!/usr/bin/env bash

VERSION=$(sed 's/\..*//' /etc/debian_version)

# debian packages
apt-get update
apt-get install -y memcached locales-all libjpeg62-turbo libjpeg-dev libpng-dev screen apache2 sqlite3 gettext ant wget ntp clamav clamav-daemon libreoffice curl build-essential systemd-timesyncd  libmagickwand-dev
apt-get install -y python3 python3-dev python3-venv python3.11-venv libapache2-mod-wsgi-py3 python3-xapian libxapian-dev python3-xapian-haystack ffmpeg

# python modules
mkdir -p /var/web/yats/
cd /var/web/yats/
python3 -m venv py_env # create your virtual environment
chmod -R a+rwx py_env
source py_env/bin/activate # Any package you install will be inside this environment

/vagrant/install_xapian.sh 1.4.22

sites=`python3 -c "import site; print(site.getsitepackages()[0])"`
ln -fs /vagrant_modules/yats $sites 2>/dev/null
ln -fs /vagrant_modules/bootstrap_toolkit $sites 2>/dev/null
ln -fs /vagrant_modules/graph $sites 2>/dev/null

pip install -r /vagrant/requirements.txt

# patch djradicale
cp /vagrant_modules/djradicale/urls.py /var/web/yats/py_env/lib/python3.11/site-packages/djradicale/urls.py

# clamav db update
systemctl stop clamav-freshclam
freshclam

# clamav config
ret=`grep -ir "TCPSocket" /etc/clamav/clamd.conf`
if [ "" = "$ret" ]; then
echo "TCPSocket 3310" >> /etc/clamav/clamd.conf
fi
ret=`grep -ir "TCPAddr" /etc/clamav/clamd.conf`
if [ "" = "$ret" ]; then
echo "TCPAddr 127.0.0.1" >> /etc/clamav/clamd.conf
fi
echo "ListenStream=127.0.0.1:3310" >> /etc/systemd/system/clamav-daemon.socket.d/extend.conf
systemctl --system daemon-reload
systemctl restart clamav-daemon.socket
systemctl restart clamav-daemon.service

# yats web
mkdir -p /var/web/yats/static
chown root:vagrant /var/web/yats/static
chmod go+w /var/web/yats/static

ln -fs /vagrant_sites/web /var/web/yats/web

mkdir -p /var/web/yats/files
chown root:vagrant /var/web/yats/files
chmod go+w /var/web/yats/files

mkdir -p /var/web/yats/logs
touch /var/web/yats/logs/django_request.log
chown root:vagrant /var/web/yats/logs/django_request.log
chmod go+w /var/web/yats/logs/django_request.log

ln -fs /vagrant_sites/caldav /var/web/yats/caldav

# yats config
mkdir -p /usr/local/yats/config
ln -fs /vagrant/web.ini /usr/local/yats/config/web.ini

# yats db
mkdir -p /var/web/yats/db
chown root:vagrant /var/web/yats/db
chmod go+w /var/web/yats/db

# yats index
mkdir -p /var/web/yats/index
chown root:vagrant /var/web/yats/index
chmod go+w /var/web/yats/index

cd /var/web/yats/web/

touch /var/web/yats/db/yats2.sqlite
chown root:vagrant /var/web/yats/db/yats2.sqlite
chmod go+w /var/web/yats/db/yats2.sqlite
python3 manage.py migrate
python3 manage.py createsuperuser --username root --email root@localhost --noinput
python3 manage.py loaddata /vagrant/init_db.json
pygmentize -S default -f html -a .codehilite > /vagrant_modules/yats/static/pygments.css
python3 manage.py collectstatic  -l --noinput

# apache config
a2enmod ssl
mkdir -p /etc/apache2/certs
cd /etc/apache2/certs
openssl genrsa -out dev.yats.net.key 2048
openssl req -new -x509 -key dev.yats.net.key -out dev.yats.net.cert -days 3650 -subj /CN=dev.yats.net
cp /vagrant/yats.apache /etc/apache2/sites-available/yats.conf
a2dissite default
a2dissite 000-default
a2ensite yats
apache2ctl restart

# testticket via API
python3 /vagrant_project/test/api_simple_create.py

# rebuid Index
python3 manage.py clear_index --noinput
python3 manage.py update_index --noinput

deactivate # get out of the isolated environment

# deb upgrade
apt-get -y upgrade &

# running ant and ignore error
cd /vagrant_project
ant ci18n

timedatectl set-ntp true

echo "open http://192.168.33.11 with user: admin password: admin"

cat <<EOF >> /home/vagrant/.bashrc
if (tty -s); then
    source /var/web/yats/py_env/bin/activate
    cd /var/web/yats/
fi
EOF
