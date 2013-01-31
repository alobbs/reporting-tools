GERRIT_OS_HOST = 'review.openstack.org'
GERRIT_OS_PORT = '29418'

# Every team is composed from a 'gerrit' and 'bugzilla' blocks, each
# one of them with their own projects and people lists.

TEAMS = {
    'ui': {
        'gerrit': {
            'query_user': 'alobbs',
            'query_host': GERRIT_OS_HOST,
            'query_port': GERRIT_OS_PORT,
            'projects':   ['horizon'],
            'people':     ['alobbs', 'jpichon', 'mrunge']
            },
        'bugzilla': {
            'projects':   ['python-django-horizon'],
            'people':     ['jpichon', 'mrunge', 'lsurette']
            },
     },

    'lab': {
        'gerrit': {
            'query_user': 'alobbs',
            'query_host': GERRIT_OS_HOST,
            'query_port': GERRIT_OS_PORT,
            'projects':   ['packstack'],
            'people':     ['derekh', 'radez', 'gildub', 'alobbs']
            },
        'bugzilla': {
            'projects': ['openstack-packstack'],
            'people':   ['derekh', 'aortega', 'dradez', 'gdubreui']
            }
     },
}
