Django Request Profiler
=======================

**This package now requires Python 3.9 and Django 3.2 and above.**

A very simple request profiler for Django.

Introduction
------------

    Premature optimization is the root of all evil.

There are a lot of very good, and complete, python and django profilers
available. They can give you detailed stack traces and function call timings,
output all the SQL statements that have been run, the templates that have been
rendered, and the state of any / all variables along the way. These tools are
great for optimisation of your application, once you have decided that the
time is right.

``django-request-profiler`` is not intended to help you optimise, but to help
you decide whether you need to optimise in the first place. It is complimentary.

Requirements
------------

1. Small enough to run in production
2. Able to configure profiling at runtime
3. Configurable to target specific URLs or users
4. Record basic request metadata:

- Duration (request-response)
- Request path, remote addr, user-agent
- Response status code, content length
- View function
- Django user and session keys (if appropriate)
- Database query count (if DEBUG=True)

It doesn't need to record all the inner timing information - the goal is to have
a system that can be used to monitor site response times, and to identify
problem areas ahead of time.

Technical details
-----------------

The profiler itself runs as Django middleware, and it simply starts a timer when
it first sees the request, and stops the timer when it is finished with the
response. It should be installed as the first middleware in
``MIDDLEWARE_CLASSES`` in order to record the maximum duration.

It hooks into the  ``process_request`` method to start the timer, the
``process_view`` method to record the view function name, and the
``process_response`` method to stop the timer, record all the request
information and store the instance.

The profiler is controlled by adding ``RuleSet`` instances which are used to
filter which requests are profiled. There can be many, overlapping,
RuleSets, but if any match, the request is profiled. The RuleSet model
defines two core matching methods:

1. uri_regex - in order to profile a subset of the site, you can supply a regex
which is used match the incoming request path. If the url matches, the request
can be profiled.

2. user_filter_type - there are three choices here - profile all users, profile
only authenticated users, and profile authenticated users belonging to a given
Group - e.g. create a groups called "profiling" and add anyone you want to
profile.

These filter properties are an AND (must pass the uri and user filter), but the
rules as a group are an OR - so if a request passes all the filters in any rule,
then it's profiled.

These filters are pretty blunt, and there are plenty of use cases where you may
want more sophisticated control over the profiling. There are two ways to do
this. The first is a setting, ``REQUEST_PROFILER_GLOBAL_EXCLUDE_FUNC``, which is
a function that takes a request as the single argument, and must return True or
False. If it returns False, the profile is cancelled, irrespective of any rules.
The primary use case for this is to exclude common requests that you are not
interested in, e.g. from search engine bots, or from Admin users etc. The
default for this function is to prevent admin user requests from being profiled.

The second control is via the ``cancel()`` method on the ``ProfilingRecord``,
which is accessible via the ``request_profile_complete`` signal. By hooking
in to this signal you can add additional processing, and optionally cancel
the profiler. A typical use case for this is to log requests that have
exceeded a set request duration threshold. In a high volume environment you
may want to, for instance, only profile a random subset of all requests.

.. code:: python

    from django.dispatch import receiver
    from request_profiler.signals import request_profile_complete

    @receiver(request_profiler_complete)
    def on_request_profile_complete(sender, **kwargs):
        profiler = kwargs.get('instance')
        if profiler.elapsed > 2:
            # log long-running requests
            # NB please don't use 'print' for real - use logging
            print u"Long-running request warning: %s" % profiler
        else:
            # calling cancel means that it won't be saved to the db
            profiler.cancel()

An additional scenario where you may want to use the signal is to store
the profiler records async - say if you are recording every request for
a short period, and you don't want to add unnecessary inline database
write operations. In this case you can use the ``stop()`` method, which
will prevent the middleware from saving it directly (it will only save
records where ``profiler.is_running`` is true, and both ``cancel`` and
``stop`` set it to false).

.. code:: python

    from django.dispatch import receiver
    from request_profiler.signals import request_profile_complete

    @receiver(request_profiler_complete)
    def on_request_profile_complete(sender, **kwargs):
        profiler = kwargs.get('instance')
        # stop the profiler to prevent it from being saved automatically
        profiler.stop()
        assert not profiler.is_running
        # add a job to a queue to perform the save itself
        queue.enqueue(profiler.save)


Installation
------------

For use as the app in Django project, use pip:

.. code:: shell

    $ pip install django-request-profiler
    # For hacking on the project, pull from Git:
    $ git pull git@github.com:yunojuno/django-request-profiler.git

Tests
-----

The app installer contains a test suite that can be run using the Django
test runner:

.. code:: shell

    $ pip install -r requirements.txt
    $ python manage.py test test_app request_profiler

If you want to test coverage you'll need to add some dependencies:

.. code:: shell

    $ pip install coverage django-coverage
    $ python manage.py test_coverage test_app request_profiler

The tests also run using `tox <https://testrun.org/tox/latest/>`_:

.. code:: shell

    $ pip install tox
    $ tox

**Note: To test with a custom user model, you should override the default User model
by providing a value for the AUTH_USER_MODEL (in testapp/settings) setting that references a custom model**

The tests run on `Travis <https://travis-ci.org/yunojuno/django-request-profiler>`_ on commits to master.

Usage
-----

Once installed, add the app and middleware to your project's settings file.
In order to add the database tables, you should run the ``migrate`` command:

.. code:: bash

    $ python manage.py migrate request_profiler

NB the middleware must be the **first** item in ``MIDDLEWARE_CLASSES``.

.. code:: python

    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'request_profiler',
    )

    MIDDLEWARE_CLASSES = [
        # this package's middleware
        'request_profiler.middleware.ProfilingMiddleware',
        # default django middleware
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ]

Configuration
-------------

To configure the app, open the admin site, and add a new request profiler
'Rule set'. The default options will result in all non-admin requests being
profiled.

Licence
-------

MIT (see LICENCE)
