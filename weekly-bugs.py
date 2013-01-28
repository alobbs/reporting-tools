#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*-

# AUTHORS:
#  Alvaro Lopez Ortega <alvaro@redhat.com>

"""
Tool for generating plain text bug summaries from RH's BZ
"""

import os
import sys
import time
import datetime
import prettytable
import logging
import argparse
import weekly_config as config

# Constants
DEFAULT_DAYS      = 7
DEFAULT_BUG_OWNER = 'rhos-maint@redhat.com'
MONTHS            = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
BUGLIST_URL       = 'https://bugzilla.redhat.com/buglist.cgi?'

# Constants: Statuses
STATUSES_ALL  = ['NEW', 'ASSIGNED', 'MODIFIED', 'ON_DEV', 'ON_QA', 'VERIFIED', 'RELEASE_PENDING', 'POST']
STATUSES_NEW  = ['NEW', 'ASSIGNED']
STATUSES_WIP  = ['ASSIGNED', 'MODIFIED', 'ON_DEV']
STATUSES_DONE = ['ON_QA', 'VERIFIED', 'RELEASE_PENDING', 'POST', 'CLOSED']
STATUS_SHORT  = {'NEW': 'New', 'ASSIGNED': 'Ass', 'MODIFIED': 'Mod', 'ON_DEV': 'Dev', 'ON_QA': 'QA', 'VERIFIED': 'Ver', 'RELEASE_PENDING': 'Rel', 'POST': 'Pst', 'CLOSED': 'Clo'}


def get_cookies():
    # Find Chrome's cookies file
    paths = [os.path.join (os.getenv('HOME'), '.config/google-chrome/Default/Cookies'),
             os.path.join (os.getenv('HOME'), 'Library/Application Support/Google/Chrome/Default/Cookies')]

    cookies_path = None
    for p in paths:
        if os.path.exists(p):
            cookies_path = p
            break

    logging.debug ("Chrome's Cookies file: %s" %(cookies_path))
    assert cookies_path, "Could not find Chrome's Cookies file"

    # Query
    while True:
        cmd = "sqlite3 -separator $'\t' \"%s\" 'select host_key, name, value from cookies' | grep bugzilla.redhat.com" %(cookies_path)
        cont = os.popen (cmd, 'r').read()
        if len(cont.split('\n')) > 3:
            break

        time.sleep(2)
        print "Trying to access Chromium's cookies..\n"

    # Parse output
    cookies = ''
    for line in cont.split('\n'):
        tmp = line.split('\t')
        if len(tmp) < 3:
            continue
        cookies += "%s=%s; " %(tmp[1], tmp[2])

    return cookies

def format_summary (txt, max_length):
    if txt[0] == '"':
        txt = txt [1:-1]

    if len(txt) < max_length:
        return txt
    else:
        return txt[:max_length-1]+'…'

def format_date (txt):
    tmp = txt[1:-1].split(' ')
    date_pieces = tmp[0].split('-')
    return MONTHS[int(date_pieces[1])-1] + ' ' + date_pieces[2]

def format_source (txt):
    txt = txt[1:-1]
    if txt == 'Red Hat OpenStack':
        return 'RHOS'
    elif txt == 'Fedora':
        return 'Fedo'
    elif txt == 'Fedora EPEL':
        return 'EPEL'
    elif txt == 'RHOS Tracking':
        return 'Task'
    else:
        return ''

def format_id_form_email (txt):
    return txt[1:-1].split('@')[0]

def format_status_to_char (txt):
    return STATUS_SHORT[txt[1:-1]]

    return txt[1:-1].split('ON_')[-1][0]

def GET (url):
    # Get cookies for accessing Bugzilla
    cookies = get_cookies()

    # Fetch page content
    cmd = 'wget -O - -q --no-cookies --header="Cookie: %s" "%s"' %(cookies, url)
    return os.popen (cmd, 'r').read()

def parse_CVS_bug_list (cont):
    bugs = []

    for line in cont.split('\n'):
        bugs.append (line.split(','))

    return bugs[1:]

def filter_bug_by_date (bug, days_num):
    d = datetime.datetime.strptime (bug[-1], '"%Y-%m-%d %H:%M:%S"')
    return time.mktime(d.timetuple()) >= time.time() - ((days_num + 3) * 24 * 60 * 60)

def URL_get_macro_devels (emails_ids, bug_statuses):
    return BUGLIST_URL + '&'.join (
        ['j_top=OR', 'query_format=advanced', 'ctype=csv', 'human=1'] +
        ['bug_status=%s'%(s) for s in bug_statuses]                   +
        ['f%s=assigned_to'%(n+1) for n in range(len(emails_ids))]     +
        ['o%s=substring'  %(n+1) for n in range(len(emails_ids))]     +
        ['v%s=%s%%40redhat.com' %(emails_ids.index(e)+1, e) for e in emails_ids])

def URL_get_macro_project (project, bug_statuses):
    return BUGLIST_URL + '&'.join (
        ['query_format=advanced', 'ctype=csv', 'human=1'] +
        ['component=%s' %(project)]                       +
        ['bug_status=%s'%(s) for s in bug_statuses])

def URL_get_macro_project_untriaged (project, bug_statuses):
    return BUGLIST_URL + '&'.join (
        ['query_format=advanced', 'ctype=csv', 'human=1', 'j_top=OR'] +
        ['component=%s' %(project)]                                   +
        ['bug_status=%s'%(s) for s in bug_statuses]                   +
        ['f1=keywords', 'o1=notsubstring', 'v1=Triaged'])


def report_bugs_summary (project):
    url = URL_get_macro_project (project, STATUSES_ALL)
    logging.debug (url)

    bugs = parse_CVS_bug_list (GET (url))

    values = []
    for s in STATUSES_ALL:
        values.append (len([b for b in bugs if b[4] == '"%s"'%(s)]))
    values = [values]

    table = prettytable.PrettyTable ([s.replace('RELEASE_PENDING','RELS_PEND').replace('MODIFIED', 'MOD') for s in STATUSES_ALL])
    table.add_row (*values)

    txt = u"➤ %s: Summary\n" %(project)
    txt += table.get_string()
    return txt

def report_bugs_untriaged (project, include_all):
    url = URL_get_macro_project_untriaged (project, STATUSES_NEW)
    logging.debug (url)

    bugs = parse_CVS_bug_list (GET (url))
    if not include_all:
        bugs2 = [b for b in bugs if b[3][1:-1] == DEFAULT_BUG_OWNER]
    else:
        bugs2 = bugs

    table = prettytable.PrettyTable (['ID', 'Src', 'Sta', 'Summary', 'Owner'], sortby='ID', reversesort=True)
    for bug in bugs2:
        table.add_row ([bug[0], format_source(bug[1]), format_status_to_char(bug[4]), format_summary(bug[6], 36), format_id_form_email(bug[3])])

    txt = u"➤ Untriaged (%d)\n" %(len(bugs2))
    txt += table.get_string()
    return txt

def report_bugs_fixed_in_recently (days_num, email_ids):
    url = URL_get_macro_devels (email_ids, STATUSES_DONE)
    logging.debug (url)

    bugs = parse_CVS_bug_list (GET (url))
    bugs2 = [b for b in bugs if filter_bug_by_date(b, days_num)]

    table = prettytable.PrettyTable (['ID', 'Src', 'Sta', 'Summary', 'Owner'], sortby='ID', reversesort=True)
    for bug in bugs2:
        table.add_row ([bug[0], format_source(bug[1]), format_status_to_char(bug[4]), format_summary(bug[6], 36), format_id_form_email(bug[3])])

    txt = u"➤ Closed in the last %d days (%d)\n" %(days_num, len(bugs2))
    txt += table.get_string()
    return txt

def report_bugs_by_engineer (email_ids):
    url = URL_get_macro_devels (email_ids, STATUSES_WIP)
    logging.debug (url)

    bugs = parse_CVS_bug_list (GET (url))

    table = prettytable.PrettyTable (['ID', 'Src', 'Sta', 'Summary', 'Owner'], sortby='ID', reversesort=True)
    for bug in bugs:
        table.add_row ([bug[0], format_source(bug[1]), format_status_to_char(bug[4]), format_summary(bug[6], 36), format_id_form_email(bug[3])])

    txt = u"➤ Bugs being fixed up (%d)\n" %(len(bugs))
    txt += table.get_string()
    return txt


def main():
    # Process command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument ('--debug',         action="store_true", default=False,        help="Debug mode (Default: No)")
    parser.add_argument ('--days',          action="store",      default=DEFAULT_DAYS, help="Number of days to cover (Default: %s)"%(DEFAULT_DAYS), type=int)
    parser.add_argument ('--untriaged-all', action="store_true", default=False,        help="Include all untriaged bugs with an owner (Default: No)")
    parser.add_argument ('team')

    ns = parser.parse_args()
    if not ns:
        print ("ERROR: Couldn't parse parameters")
        raise SystemExit

    if not config.TEAMS.has_key (ns.team):
        print ("ERROR: Team not in the list. Please, check weekly_config.py")
        raise SystemExit

    team = config.TEAMS[ns.team]

    # Logging
    if ns.debug:
        logging.basicConfig (level=logging.DEBUG)

    # Reports
    for project in team['projects']:
        print report_bugs_summary (project)
        print
        print report_bugs_untriaged (project, ns.untriaged_all)
        print

    print report_bugs_fixed_in_recently (ns.days, team['people'])
    print
    print report_bugs_by_engineer (team['people'])
    print


if __name__ == '__main__':
    main()
