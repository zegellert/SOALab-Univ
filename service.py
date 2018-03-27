#!/usr/bin/env python
# pylint: disable=invalid-name

"""
    Databases Laboratory 5
    SOA service demo

    This sample service was created for the purposes of demonstrating some
    of the functionality you can achieve by combining the power of three
    Python libraries: cx_Oracle, Flask, and Requests.

    It does not intend to be perfect Python code -- in some places, perfection
    was traded for simplicity, some of these are marked in comments.

    This comment is a so-called docstring, all Python modules and
    functions/methods should have one. Three " or ' characters make it
    possible for multiline strings, and interactive Python environments
    display these "docstrings" (basically header comments) for users of
    your code. Further info: http://www.python.org/dev/peps/pep-0257/
"""

from datetime import datetime
from datetime import date
import json

from flask import Flask, jsonify, abort, request
import cx_Oracle
import requests

app = Flask(__name__)

@app.route('/szemelyek.json')
def list_people():
    """Lists the first 50 persons in the database"""
    conn = get_db()
    try:
        cur = conn.cursor()
        try:
            # Note: don't use prefixes like "oktatas." above for tables
            # within your own schema, as it ruins portability.
            # This table has 10k rows, so we intentionally limit the result set to 50
            # (Oracle note: not the first 50 rows by name, but rather
            # the first 50 rows of the table, which are then ordered by name).
            # Also, long queries can be broken into two shorter lines like this
            cur.execute('''SELECT szemelyi_szam, nev FROM oktatas.szemelyek
                WHERE ROWNUM < 50 ORDER BY nev ASC''')
            # there's a better way, but outside the scope of this lab:
            # http://docs.python.org/2/tutorial/datastructures.html#list-comprehensions
            results = []
            # we make use of the fact that
            #  - cursors are iterable and
            #  - `for` can unpack objects returned by each iteration
            for szemelyi_szam, nev in cur:
                results.append({'szemelyi_szam': szemelyi_szam, 'nev': nev})
            return jsonify(szemelyek=results)
        finally:
            cur.close()
    finally:
        # this is also a naive implementation, a more Pythonic solution:
        # http://docs.python.org/2/library/contextlib.html#contextlib.closing
        conn.close()
		
@app.route('/hallgatok.json')
def list_students():
    """Lists the students in the database"""
    conn = get_db()
    try:
        cur = conn.cursor()
        try:
           
            cur.execute('SELECT POSEIDONKOD,NEV,SZULETESIDATUM FROM HALLGATOK')
          
            results = []
        
            for poseidonkod,nev,szuletesidatum in cur:
                results.append({'PoseidonKod': poseidonkod, 'Nev': nev,'SzuletesiDatum':date.isoformat(szuletesidatum)})
            return jsonify(hallgatok=results)
        finally:
            cur.close()
    finally:
        # this is also a naive implementation, a more Pythonic solution:
        # http://docs.python.org/2/library/contextlib.html#contextlib.closing
        conn.close()
	
@app.route('/hallgatok/<pos>.json')
def list_student_bypos(pos):
    """Lists the students in the database with given PS code"""
    conn = get_db()
    try:
        cur = conn.cursor()
        try:
            cur.execute('SELECT NEV,SZULETESIDATUM,CIM,EGYETEMKEZDESEVE FROM HALLGATOK WHERE POSEIDONKOD=:pkod',pkod=pos)
            result = cur.fetchone()
            if result is None:
                abort(404)
            return jsonify(cur.fetchone().nev)
        finally:
            cur.close()
    finally:
        conn.close()


@app.route('/szemely/<szemelyi_szam>.json')
def show_person(szemelyi_szam):
    """Shows the details of a single person by szemelyi_szam"""
    conn = get_db()
    try:
        cur = conn.cursor()
        try:
            # Note: don't use prefixes like "oktatas." above for tables
            # within your own schema, as it ruins portability
            cur.execute('SELECT nev FROM oktatas.szemelyek WHERE szemelyi_szam = :sz',
                        sz=szemelyi_szam)
            # fetchone() returns a single row if there's one, otherwise None
            result = cur.fetchone()
            # in Python '==' compares by value, 'is' compares by reference
            # (of course, former would work too, but it's slower and unnecessary)
            # 'None' is the Python version of null, it's a singleton object, so
            # we can safely compare to it using 'is' (Java/C#: result == null)
            if result is None:
                # no rows -> 404 Not Found (no need to return manually)
                abort(404)
            links = []
            try:
                # we query the Wikipedia API to see what happened the day
                # the person was born based on szemelyi_szam
                born = datetime.strptime(szemelyi_szam[1:7], '%y%m%d')
                params = {
                    'action': 'query',
                    # 2012-04-01 -> "April 01" -> "April 1"
                    'titles': born.strftime('%B %d').replace('0', ''),
                    'prop': 'extlinks',
                    'format': 'json',
                    }
                # API docs: http://www.mediawiki.org/wiki/API:Tutorial
                # Example for 1st April:
                # https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extlinks&titles=April%201
                res = requests.get('https://en.wikipedia.org/w/api.php', params=params)
                for page in res.json()['query']['pages'].itervalues():
                    for link in page['extlinks']:
                        for href in link.itervalues():
                            links.append(href)
            except IOError:
                pass # necessary if a clause would be empty in Python

            # result set rows can be indexed too
            return jsonify(nev=result[0], links=links)
        finally:
            cur.close()
    finally:
        conn.close()

@app.route('/datetest.json')
def date_test():
    """Demonstrates handling dates from databases and formatting it according to ISO 8601"""
    conn = get_db()
    try:
        cur = conn.cursor()
        try:
            # Note: don't use prefixes like "oktatas." above for tables
            # within your own schema, as it ruins portability
            # http://www.oracle.com/technetwork/articles/dsl/prez-python-timesanddates-093014.html
            # https://docs.python.org/2/library/datetime.html
            # it's casted automatically to datetime
            cur.execute('SELECT datum, usd FROM oktatas.mnb_deviza where id < 10')
            results = []
            for datum, usd in cur:
                results.append({'datum': datum, 'datum_iso' : datum.isoformat(), 'usd': usd})
            return jsonify(arfolyamok=results)
        finally:
            cur.close()
    finally:
        conn.close()


@app.route('/verbtest.json', methods=['PUT', 'POST'])
def verb_test():
    """Lets you test HTTP verbs different from GET, expects and returns data in JSON format"""
    # it also shows you how to access the method used and the decoded JSON data
    return jsonify(method=request.method, data=request.get_json(), url=request.url)


def get_db():
    """Connects to the RDBMS and returns a connection object"""
    # when used with a `file` object, `with` ensures it gets closed
    # pylint: disable=no-member
    with file('config.json') as config_file:
        config = json.load(config_file)
    return cx_Oracle.connect(config['user'], config['pass'], config['host'])


if __name__ == "__main__":
    # pylint: disable=bad-option-value,wrong-import-position,wrong-import-order
    import os
    os.environ['NLS_LANG'] = '.UTF8'
    app.run(debug=True, port=os.getuid() + 10000)
