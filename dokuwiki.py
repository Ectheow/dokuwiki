import requests
import sys
import xml.etree.ElementTree as ET
import getpass
import argparse
from . import xmlrpc

class DokuWikiError(RuntimeError):
    def __init__(self, string, xml, response):
        if not string:
            string = ''
        if not xml:
            xml = ''

        self._error_string = (
            "DokuWiki error: {}. \nXML:\n{}\nHTTP Response {}:\n{}"
            .format(
                string,
                xml,
                response.status_code if response is not None else '<no status code>',
                response.text.encode('utf-8', errors='ignore') if response is not None else '<no text>'))

    def __str__(self):
        return self._error_string

class DokuWiki:
    '''
    A class representing a DokuWiki, using the XML RPC
    to communicate with it and do simple manipulations.
    https://en.wikipedia.org/wiki/XML-RPC
    https://www.dokuwiki.org/devel:xmlrpc
    '''

    RPC_PATH="/lib/exe/xmlrpc.php"

    def __init__(self, url, verify=True):
        self.url=url+DokuWiki.RPC_PATH
        self.version = None
        self.rpc_client = xmlrpc.XMLRPCClient(self.url, verify=verify)
        self.version = self.rpc_client.call('dokuwiki.getVersion')[0]

    def get_page(self, pagename):
        return self.rpc_client.call('wiki.getPage', pagename)[0]

    def put_page(self, pagename, pagetext):
        return self.rpc_client.call('wiki.putPage',
                                    pagename, pagetext)[0]
    def get_page_html(self, pagename):
        return self.rpc_client.call('wiki.getPageHTML', pagename)[0]

    def lock(self, page):
        result = self.rpc_client.call('dokuwiki.setLocks',
                                    {'lock':
                                    [page],
                                    'unlock':
                                    []})[0]
        if page in result['locked']:
            return True
        elif page in result['lockfail']:
            return False



    def login(self, username, password):
        return self.rpc_client.call('dokuwiki.login',
                                    username, password)[0]

'''
Demo program for fetching dokuwiki stuff using XML RPC
'''

def main(url,
        page,
        action,
        nologin,
        input_file,
        output_file,
        verify=True):

    wiki = DokuWiki(url, verify=verify)

    if not nologin:
        username = raw_input('username > ')
        password = getpass.getpass('password > ')
        if not wiki.login(username, password):
            print("could not log in")
            raise SystemExit(1)
        else:
            print("logged in OK.")

    #print(wiki.version)

    if action == 'get':
        output_file.write(wiki.get_page(page))
    elif action == 'put':
        wikitext=''
        for line in iter(input_file.readline, ''):
            wikitext += line
        wiki.put_page(page, wikitext)
    elif action == 'lock':
        if wiki.lock(page):
            print('OK')
        else:
            print("can't lock page " + page)
    else:
        print('undefined action')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process dokuwiki arguments")
    parser.add_argument('--nologin',
                        dest='nologin',
                        action='store_true',
                        default=False)
    parser.add_argument('--noverify',
                        dest='noverify',
                        action='store_true',
                        default=False)
    parser.add_argument('url', nargs=1)
    parser.add_argument('page', nargs=1)
    parser.add_argument('action', nargs=1)
    parser.add_argument('output_file', nargs='?', default='')
    parser.add_argument('input_file', nargs='?', default='')
    params = parser.parse_args(sys.argv[1:])

    i = None
    if params.input_file == '':
        i = sys.stdin
    else:
        i = open(params.input_file, 'r')

    o = None
    if params.output_file == '':
        o = sys.stdout
    else:
        o = open(params.output_file, 'w')

    with o as out, i as inp:
        main(url=params.url[0],
             page=params.page[0],
             action=params.action[0],
             nologin=params.nologin,
             input_file=inp,
             output_file=out,
             verify=(not params.noverify))

