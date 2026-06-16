#!/usr/bin/env bash
set -e

# NOTE: the Xapian C bindings are provided by the apt package `python3-xapian`
# installed in the Dockerfile; there is no /vagrant/install_xapian.sh in the
# image (that path only exists in the Vagrant box). Source-building Xapian here
# is unnecessary.

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python -m gunicorn --bind 0.0.0.0:8000 --workers 3 django_project.wsgi:application