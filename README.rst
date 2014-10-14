django-request-profiler
=======================

A very simple request profiler for Django.

Introduction
------------

> Premature optimization is the root of all evil.

There are a lot of very good, and complete, python and django profilers
available. They can give you detailed stack traces and function call timings,
output all the SQL statements that have been run, the templates that have been
rendered, and the state of any / all variables along the way. These tools are
great for optimisation (sic) of your application, once you have decided that the
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
- URL
- Source IP
- User-Agent
- View function
- Django user and session keys (if appropriate)

It doesn’t need to record all the inner timing information - the goal is to have
a system that can be used to monitor site response times, and to identify
problem areas ahead of time.

Technical details
-----------------

The profiler itself runs as Django middleware, and it simply starts a timer when
it first sees the request, and stops the timer when it is finished with the
response. It should be installed as the first middleware in
``MIDDLEWARE_CLASSES`` in order to record the maximum duration.

It hooks into the ``process_request`` method to start the timer, the
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

2. user_group - in order to profile a subset of users, you can supply the name
of a Django ``Group`` against which users are matched. If they are in the group,
the request can be profiled.

In addition, each RuleSet has an ``include_anonymous`` flag - as you may
want to ignore unauthenticated users.

There is a single global setting, ``IGNORE_STAFF``, which is True by default -
this means that any user with ``is_staff==True`` will be ignored.

Once an incoming request has been evaluated by all of the rules, if any match,
the request can be saved. There is, however, one final check which is used to
provide ultimate control over the filtering. Before the profile record is saved,
a signal is sent (``request_profile_complete``). If any signal receivers return
False, then the profile is thrown away.

This signal can be used to hook in custom rules - for instance, restricting by
IP, or user agent, or even custom properties.

Installation
------------

For use as the app in Django project, use pip:

.. code:: shell

    $ pip install django-request—profiler
    # For hacking on the project, pull from Git:
    $ git pull git@github.com:yunojuno/django-request-profiler.git

Usage
-----

Once installed, add the app and middleware to your project’s settings file.

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
