+++++
ABCdb
+++++

|license| |build| |docs|

.. |license| image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://en.wikipedia.org/wiki/MIT_License
   :alt: MIT Licensed

.. |build| image:: https://travis-ci.org/smbolton/abcdb.svg?branch=master
   :target: https://travis-ci.org/smbolton/abcdb
   :alt: Documentation Status

.. |docs| image:: https://readthedocs.org/projects/abcdb/badge/?version=latest
   :target: http://abcdb.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

ABCdb is a web-based tool for working with music notated in ABC
format, providing database, deduplication, rendering, and analysis functions.

Documentation
=============

You may read the full documentation on `Read the Docs <http://abcdb.readthedocs.io/en/latest/>`_.

Installation
============

ABCdb is a fairly straightforward Django project. It requires the following
packages:

  * `Python 3.5 <https://www.python.org/>`_
  * `Django 1.10 <https:/www.djangoproject.com/>`_
  * `pytz 2016.10 <https://pythonhosted.org/pytz/>`_
  * `requests 2.12.5 <https://github.com/kennethreitz/requests>`_
  * `Arpeggio 1.5 <https://github.com/igordejanovic/Arpeggio>`_

Additional, two environment variables must be set:

  * ``ABCDB_SECRET_KEY`` - Set this to the database key.

  * ``ABCDB_DEPLOYMENT`` - Set this to either 'development' or 'production'.
    When using 'development', ``settings.DEBUG`` is set to ``True``. When using 'production',
    ``settings.DEBUG`` is ``False``, and there is more configuration you will need to do in
    ``settings.DEBUG``.

A simple demonstration installation, using the Django development server, can be made something
like this:

.. code:: shell

   $ virtualenv abcdb-test
   $ cd abcdb-test
   $ source ./bin/activate
   $ git clone https://github.com/smbolton/abcdb.git abcdb
   $ cd abcdb
   $ pip install -r requirements.txt
   $ export ABCDB_SECRET_KEY='somE_secreT_databasE_keY'
   $ export ABCDB_DEPLOYMENT='development'
   $ python manage.py makemigrations
   $ python manage.py migrate
   $ python manage.py createsuperuser --username=admin --email=none@example.com  # will ask for password
   $ python manage.py runserver

Point your browser at the development server URL (http://127.0.0.1:8000/ by default), and log in
as 'admin' to access all ABCdb functions. See the
`Usage <http://abcdb.readthedocs.io/en/latest/#usage>`_ section of the documentation for details.

License
=======

All code original to the ABCdb project is licensed under the `MIT/Expat
License <https://en.wikipedia.org/wiki/MIT_License>`_:

  Copyright © 2017 Sean Bolton.

  Permission is hereby granted, free of charge, to any person obtaining
  a copy of this software and associated documentation files (the
  "Software"), to deal in the Software without restriction, including
  without limitation the rights to use, copy, modify, merge, publish,
  distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so, subject to
  the following conditions:

  The above copyright notice and this permission notice shall be
  included in all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
  LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

All included code (e.g. CSS or ./manage.py) is licensed under similar
non-copyleft licenses. See the file
`LICENSES <https://github.com/smbolton/abcdb/blob/master/LICENSES>`_ for more
information.
