#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-

# AUTHORS:
#  Alvaro Lopez Ortega <alvaro@redhat.com>

"""
Tool for generating plain text bug summaries from Openstack's Gerrit
"""

import os
import re
import time
import json
import datetime
import StringIO
import prettytable
import argparse
import getpass
import weekly_config as config

# Defaults
DEFAULT_DAYS = 7
DEFAULT_SRV = 'review.openstack.org'
DEFAULT_PORT = 29418

# Contants
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def parse(txt):
    data = []
    for line in txt.split('\n'):
        if not '{' in line:
            continue
        o = json.load(StringIO.StringIO(line))
        data.append(o)

    return data


def sort_rows(x):
    tmp = x[0].split(' ')
    return ((MONTHS.index(tmp[0]) + 1) * 30) + int(tmp[1])


def format_date(ts):
    dt = datetime.datetime.fromtimestamp(ts)
    return MONTHS[dt.month - 1] + ' ' + dt.strftime("%d")


def format_subject(txt):
    MAXLEN = 38
    if len(txt) < MAXLEN:
        return txt
    else:
        return txt[:MAXLEN - 1] + u'…'


def filter_data_from_time(data, from_time):
    return [l for l in data if 'subject' in l.keys() and
            l['lastUpdated'] >= from_time]


def render_owners(data, from_time):
    table = prettytable.PrettyTable(['Dev', 'Subject', 'ID', 'Date'],
                                    sortby='Date', sort_key=sort_rows,
                                    reversesort=True)
    for line in data:
        table.add_row([line['owner']['username'],
                      format_subject(line['subject']),
                      line['number'], format_date(line['lastUpdated'])])
    return table.get_string()


def render_reviewers(data, from_time):
    table = prettytable.PrettyTable(['Reviewer', 'Subject', 'ID', 'Date'],
                                    sortby='Date', sort_key=sort_rows,
                                    reversesort=True)
    for line in data:
        table.add_row([line['searched_for'],
                      format_subject(line['subject']),
                      line['number'], format_date(line['lastUpdated'])])
    return table.get_string()


def run_query(search_field, project, people, user, server, port):
    data = []

    for nick in people:
        # Query
        query = ("%(search_field)s:%(nick)s@redhat.com AND "
                 "project:openstack/%(project)s" % (locals()))
        #  AND age:%(AGE)s

        # Excute
        cmd = ("ssh %(user)s@%(server)s -p %(port)s gerrit query "
               "--format=JSON \"%(query)s\"" % (locals()))
        f = os.popen(cmd, 'r')
        cont = f.read()

        # Parse
        d = parse(cont)
        for entry in d:
            entry['searched_for'] = nick
        data += d
    return data


def main():
    # Process command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action="store_true", default=False,
                        help="Debug mode (Default: No)")
    parser.add_argument('--days', action="store", default=DEFAULT_DAYS,
                        help="Number of days to cover (Default: %s)"
                        % (DEFAULT_DAYS), type=int)
    parser.add_argument('team')

    ns = parser.parse_args()
    if not ns:
        print ("ERROR: Couldn't parse parameters")
        raise SystemExit

    if ns.team not in config.TEAMS:
        print ("ERROR: Team not in the list. Please, check weekly_config.py")
        raise SystemExit

    gerrit = config.TEAMS[ns.team]['gerrit']

    # Logging
    if ns.debug:
        logging.basicConfig(level=logging.DEBUG)

    from_time = time.time() - ((ns.days + 3) * 24 * 60 * 60)
    user = gerrit.get('query_user',   getpass.getuser())
    server = gerrit.get('query_server', DEFAULT_SRV)
    port = gerrit.get('query_port',   DEFAULT_PORT)

    # Reports
    queries = {'owner':    'Review owners',
               'reviewer': 'Reviews'}

    for project in gerrit['projects']:
        for q_type in queries:
            data = run_query(q_type, project, gerrit['people'], user, server,
                             port)
            data = filter_data_from_time(data, from_time)
            if data:
                print "➤ %s: %s (%d)" % (queries[q_type], project, len(data))
                if q_type == 'owner':
                    print render_owners(data, from_time)
                else:
                    print render_reviewers(data, from_time)
                print


if __name__ == '__main__':
    main()
