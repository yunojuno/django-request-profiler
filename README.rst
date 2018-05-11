.. image:: https://badge.fury.io/py/django-request-profiler.svg
    :target: https://badge.fury.io/py/django-request-profiler

.. image:: https://travis-ci.org/yunojuno/django-request-profiler.svg
    :target: https://travis-ci.org/yunojuno/django-request-profiler

Django Request Profiler
=======================

**This package now requires Python3 and Django1.11 and above. For previous versions please refer to the Python2 branch.**

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

It doesn't need to record all the inner timing information - the goal is to have
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


Installation
------------

This app has dropped support for Django < 1.7, since v0.11.

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


## 한국어

.. image:: https://badge.fury.io/py/django-request-profiler.svg
    :target: https://badge.fury.io/py/django-request-profiler

.. image:: https://travis-ci.org/yunojuno/django-request-profiler.svg
    :target: https://travis-ci.org/yunojuno/django-request-profiler

장고 요청 프로파일 러
===========

**이 패키지에는 이제 Python3 및 Django1.11 이상이 필요합니다. 이전 버전의 경우 Python2 분기를 참조하십시오. **

Django에 대한 매우 간단한 요청 프로파일 러입니다.

소개
------------

    조숙 한 최적화는 모든 악의 근원입니다.

매우 훌륭하고 완전한 python 및 django 프로파일 러가 많이 있습니다.
유효한. 그들은 상세한 스택 트레이스와 함수 호출 타이밍을 줄 수 있으며,
실행 된 모든 SQL 문을 출력하고,
렌더링 된 상태, 길을 따라 / 모든 변수의 상태. 이 도구들은
귀하의 응용 프로그램을 최적화하는 데 큰 도움이됩니다.


``django-request-profiler``는 최적화를 돕는 것이 아니라 도움을주기위한 것입니다.
당신은 처음부터 최적화 할 필요가 있는지 결정합니다. 그것은 무료입니다.

요구 사항
------------

1. 프로덕션 환경에서 실행하기에 충분히 작은 크기
2. 런타임에 프로파일 링을 구성 할 수 있습니다.
3. 특정 URL 또는 사용자를 타겟팅하도록 구성 가능
4. 기본 요청 메타 데이터 기록 :

- 기간 (요청 - 응답)
- 요청 경로, 원격 주소, 사용자 에이전트
- 응답 상태 코드, 콘텐츠 길이
-보기 기능
- 장고 사용자 및 세션 키 (해당되는 경우)

모든 내부 타이밍 정보를 기록 할 필요는 없습니다.
사이트 응답 시간을 모니터링하는 데 사용할 수있는 시스템
문제 영역을 사전에 확인하십시오.

기술적 세부 사항
-----------------

프로파일 러 자체는 Django 미들웨어로 실행되며 타이머가 시작됩니다.
먼저 요청을보고 타이머가 끝나면 타이머를 중지합니다.
응답. 첫 번째 미들웨어로 설치해야합니다.
최대 지속 시간을 기록하기 위해``MIDDLEWARE_CLASSES``를 사용하십시오.

타이머를 시작하기 위해``process_request`` 메소드에 후킹합니다.
뷰 함수 이름을 기록하는``process_view`` 메소드와
``process_response`` 메소드는 타이머를 멈추고, 모든 요청을 기록합니다.
정보를 저장하고 인스턴스를 저장하십시오.

프로파일 러는 "RuleSet"인스턴스를 추가하여 제어됩니다.
요청을 프로파일 링하는 필터 많은 부분이 겹칠 수 있으며,
RuleSets. 그러나 일치하는 경우 요청이 프로파일 링됩니다. RuleSet 모델
두 가지 핵심 매칭 메소드를 정의합니다.

1. uri_regex - 사이트의 하위 집합을 프로파일 링하기 위해 정규식을 제공 할 수 있습니다.
들어오는 요청 경로와 일치하는 데 사용됩니다. URL이 일치하면 요청
프로파일 링 될 수 있습니다.

2. user_filter_type - 세 가지 선택 사항이 있습니다 - 모든 사용자 프로필, 프로필
인증 된 사용자 만, 프로필에 인증 된 사용자는 주어진그룹 
- 예 : "프로파일 링"이라는 그룹을 만들고 원하는 사람을 추가하십시오.


이러한 필터 속성은 AND (uri 및 user 필터를 통과해야 함)이지만
그룹의 규칙은 OR입니다. 따라서 요청이 규칙의 모든 필터를 통과하면,
그리고 나서 그것은 프로파일 링됩니다.

이 필터는 꽤 깔끔하지 않고 사용 사례가 많이 있습니다.
프로파일 링에 대한보다 정교한 제어가 필요합니다. 두 가지 방법이 있습니다.
이. 첫 번째 설정은``REQUEST_PROFILER_GLOBAL_EXCLUDE_FUNC``입니다.
단일 인수로 요청을 받고 True를 반환해야하는 함수 또는
그릇된. False를 반환하면 규칙에 관계없이 프로필이 취소됩니다.
이를위한 기본 사용 사례는 사용자가 아닌 일반적인 요청을 제외하는 것입니다
에 관심이있다. 검색 엔진 봇 또는 관리자 사용자 등.
이 기능의 기본값은 관리자 사용자 요청이 프로파일되지 않도록하는 것입니다.

두 번째 컨트롤은``ProfilingRecord``에있는``cancel ()``메소드를 통해 이루어지며,
이것은``request_profile_complete`` 시그널을 통해 접근 가능합니다. 후크로
이 신호에 추가 처리를 추가하고 선택적으로 취소 할 수 있습니다.
프로파일 러. 일반적인 사용 사례는 다음과 같은 요청을 기록하는 것입니다.
설정된 요청 지속 시간 임계 값을 초과했습니다. 높은 볼륨 환경에서
예를 들어 모든 요청의 무작위 하위 집합 만 프로파일 링하려고 할 수 있습니다.

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

설치
------------

이 앱은 v0.11부터 Django <1.7에 대한 지원을 중단했습니다.

Django 프로젝트에서 앱으로 사용하려면 pip를 사용하십시오.

.. code:: shell

    $ pip install django-request-profiler
    # For hacking on the project, pull from Git:
    $ git pull git@github.com:yunojuno/django-request-profiler.git

테스트
-----

앱 설치 프로그램에는 Django를 사용하여 실행할 수있는 테스트 스위트가 포함되어 있습니다.
테스트 주자 :

.. code:: shell

    $ pip install -r requirements.txt
    $ python manage.py test test_app request_profiler

적용 범위를 테스트하려면 몇 가지 종속성을 추가해야합니다.

.. code:: shell

    $ pip install coverage django-coverage
    $ python manage.py test_coverage test_app request_profiler


테스트는 `tox <https://testrun.org/tox/latest/>`_ :

.. code:: shell

    $ pip install tox
    $ tox

** 참고 : 사용자 지정 사용자 모델로 테스트하려면 기본 사용자 모델을 재정의해야합니다
사용자 정의 모델을 참조하는 AUTH_USER_MODEL (testapp / settings에서) 설정 값을 제공하여 **

테스트는`Travis <https://travis-ci.org/yunojuno/django-request-profiler>`_에서 실행되어 마스터에게 커밋됩니다.

용법
-----

설치가 끝나면 앱 및 미들웨어를 프로젝트의 설정 파일에 추가하십시오.
데이터베이스 테이블을 추가하려면,``migrate`` 명령을 실행해야합니다 :

.. code:: bash

    $ python manage.py migrate request_profiler

주의 : 미들웨어는``MIDDLEWARE_CLASSES``의 ** 처음 ** 항목이어야합니다.

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
    
구성
-------------

앱을 구성하려면 관리 사이트를 열고 새 요청 프로파일 러를 추가하십시오.
'규칙 집합'. 기본 옵션을 사용하면 관리자가 아닌 모든 요청이 발생합니다.
프로파일.

특허
-------

MIT (라이센스 참조)
