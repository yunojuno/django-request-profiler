
import datetime

from django.contrib.auth.models import User

from models import RuleSet, ProfilingRecord


class ProfilingMiddleware(object):

    def process_request(self, request):
        # start the timer
        start_ts = datetime.datetime.utcnow()

        # record inbound request values
        request.profile_data = {
            'start_ts': start_ts,
            'method': request.method,
            'uri': request.build_absolute_uri(),
            'remote_addr': request.META.get('REMOTE_ADDR'),
            'http_user_agent': request.META.get('HTTP_USER_AGENT'),
            'template_render_count': 0,
        }

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.profile_data['view_func_name'] = view_func.__name__

    def process_template_response(self, request, response):
        return response

    def process_response(self, request, response):
        # stop the timer
        end_ts = datetime.datetime.utcnow()

        # record session- and user-related values
        # (available only now, after all middleware has finished)
        request.profile_data['session_key'] = request.session.session_key
        request.profile_data['user_id'] = request.user.id
        request.profile_data['response_status_code'] = response.status_code

        # record end timestamp and duration
        request.profile_data['end_ts'] = end_ts
        request.profile_data['duration'] = (
            request.profile_data['end_ts'] - request.profile_data['start_ts']
        ).total_seconds()

        # add duration header to response
        response['X-Request-Duration'] = request.profile_data['duration']

        # match and record profile data
        self.match_and_record_profile_data(request.profile_data)
        return response

    def get_first_matching_ruleset(self, profile_data):
        user = User.objects.filter(id=profile_data.get('user_id')).first()
        for ruleset in RuleSet.objects.filter(enabled=True):
            if ruleset.matches(
                uri=profile_data['uri'],
                user=user
            ):
                return ruleset
        else:
            return None

    def match_and_record_profile_data(self, profile_data):
        matching_ruleset = self.get_first_matching_ruleset(profile_data)
        if matching_ruleset:
            record = ProfilingRecord(
                ruleset=matching_ruleset,
                start_ts=profile_data['start_ts'],
                end_ts=profile_data['end_ts'],
                duration=profile_data['duration'],
                method=profile_data['method'],
                uri=profile_data['uri'],
                remote_addr=profile_data['remote_addr'],
                http_user_agent=profile_data['http_user_agent'],
                session_key=profile_data['session_key'],
                user_id=profile_data['user_id'],
                view_func_name=profile_data['view_func_name'],
                response_status_code=profile_data['response_status_code'],
                template_render_count=profile_data['template_render_count'],
            )
            record.save()
