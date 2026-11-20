# (c) Copyright 2026 Hewlett Packard Enterprise Development LP
#
# BSD 3-Clause License, see the LICENSE file at the root of this repository.

"""
WSGI middleware that makes request paths case-insensitive and tolerant of a trailing slash.

Real iLO links are lowercase and end in a slash (for example /redfish/v1/systems/1/bios/settings/) and iLO accepts
those links with any method. Flask routes are case-sensitive and the rules are registered without a trailing slash,
so a request that follows an advertised link only reaches the catch-all GET route (/redfish/v1/<path:path>) and any
other method gets a 405. The middleware rewrites the path to the canonical form of the specific rule it matches.
Rules with a <path:...> converter, such as the catch-all, are ignored.
"""


class PathNormalizer(object):

    def __init__(self, wsgi_app, flask_app):
        self.wsgi_app = wsgi_app
        self.flask_app = flask_app
        self._rule_count = -1
        self._rules = []

    def __call__(self, environ, start_response):
        environ['PATH_INFO'] = self.normalize(environ.get('PATH_INFO', ''))
        return self.wsgi_app(environ, start_response)

    def normalize(self, path):
        trimmed = path.rstrip('/') if len(path) > 1 else path
        segments = trimmed.split('/')
        canonical = None
        for rule_segments, slashed in self._candidate_rules(len(segments)):
            if self._matches(segments, rule_segments, True):
                # keep the slash for a rule that is registered with one
                return path if slashed and path != trimmed else trimmed
            if canonical is None and self._matches(segments, rule_segments, False):
                canonical = '/'.join(
                    actual if self._is_variable(expected) else expected
                    for actual, expected in zip(segments, rule_segments))
        return canonical if canonical is not None else path

    def _candidate_rules(self, segment_count):
        rules = list(self.flask_app.url_map.iter_rules())
        if len(rules) != self._rule_count:
            self._rule_count = len(rules)
            self._rules = [(r.rule.rstrip('/').split('/'), r.rule.endswith('/')) for r in rules if '<path:' not in r.rule]
        return [rule for rule in self._rules if len(rule[0]) == segment_count]

    @staticmethod
    def _is_variable(segment):
        return segment.startswith('<') and segment.endswith('>')

    @classmethod
    def _matches(cls, segments, rule_segments, case_sensitive):
        for actual, expected in zip(segments, rule_segments):
            if cls._is_variable(expected):
                continue
            if case_sensitive and actual != expected:
                return False
            if not case_sensitive and actual.lower() != expected.lower():
                return False
        return True
