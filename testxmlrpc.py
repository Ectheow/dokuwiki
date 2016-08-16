import unittest
import xmlrpc
import re
import BaseHTTPServer
import threading
import time
from SocketServer import ThreadingMixIn

class TestXMLRPCClient(unittest.TestCase):

    SERVER_PORT=9080
    SERVER_HOST='localhost'
    class XMLRPCServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        def do_POST(self):
            #text = self.rfile.read()
            self.rfile.close()
            self.log_request()
            self.log_message('POST')
            self.send_response(200, 'OK')
            self.send_header('Content-Type', 'text/xml')
            self.end_headers()
            self.wfile.write(u'''<?xml version="1.0" encoding="utf8"?>
                <methodResponse>
                    <params>
                        <param>
                        <string>hello world</string>
                        </param>
                    </params>
                </methodResponse>'''.encode('ASCII'))
            self.wfile.close()

        def do_GET(self):
            self.log_message('GET')
            self.send_response(200, 'OK')
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write('cats')
            self.wfile.close()



    class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
        pass

    class XMLRPCServerThread(threading.Thread):
        def run(self):
            self.server.serve_forever()

    def setUp(self):
        self.server_thread = TestXMLRPCClient.XMLRPCServerThread()
        self.server = TestXMLRPCClient.ThreadedHTTPServer((TestXMLRPCClient.SERVER_HOST,
                                                           TestXMLRPCClient.SERVER_PORT),
                                                           TestXMLRPCClient.XMLRPCServerHandler)
        self.server_thread.server = self.server
        self.server_thread.start()


    def test_client(self):
        #time.sleep(10)
        client = xmlrpc.XMLRPCClient('http://{}:{}/'.format(
            TestXMLRPCClient.SERVER_HOST, 
            TestXMLRPCClient.SERVER_PORT))
        return_list_shouldbe=['hello world']
        return_list = client.call('helloWorld')
        self.assertEqual(return_list, return_list_shouldbe)
    def tearDown(self):
        self.server.shutdown()

class TextXMLRPCDecode(unittest.TestCase):
    def test_decode_params_str(self):
        decode_shouldbe=['hello']
        to_decode=re.sub(r'\s+', '', '''
        <params>
            <param><string>hello</string></param>
        </params>''')
    
        decoded = xmlrpc.decode_parameters(to_decode)
        self.assertEqual(decoded, decode_shouldbe)
    
    def test_decode_params_array(self):
        decode_shouldbe=[[1, 2, 3]]
        to_decode=re.sub(r'\s+', '', '''
        <params>
            <param>
            <array>
                <data>
                 <value><int>1</int></value>
                <value><int>2</int></value>
                <value><int>3</int></value>
                </data>
            </array>
            </param>
        </params>''')
        decoded = xmlrpc.decode_parameters(to_decode)
        self.assertEqual(decoded, decode_shouldbe)

    def test_decode_struct(self):
        decode_shouldbe = [{'a':1, 'b':2, 'c':[1, 2, 3]}]
        to_decode = re.sub(r'\s+', '', '''
        <params>
            <param>
                <struct>
                    <member>
                    <name>a</name>
                    <value><int>1</int></value>
                    </member>

                    <member>
                    <name>b</name>
                    <value><int>2</int></value>
                    </member>

                    <member>
                    <name>c</name>
                    <value>
                        <array><data>
                        <value><int>1</int></value>
                        <value><int>2</int></value>
                        <value><int>3</int></value>
                        </data></array>
                    </value>
                    </member>
                </struct>
            </param>
        </params>''')
        decoded = xmlrpc.decode_parameters(to_decode)
        self.assertEqual(len(decode_shouldbe), len(decoded))
        self.assertDictEqual(decoded[0], decode_shouldbe[0])


class TestXMLRPCEncode(unittest.TestCase):
    def test_encode_params_str(self):
        params_shouldbe=re.sub(r'\s+', '', '''
        <params>
            <param><string>a</string></param>
            <param><string>b</string></param>
            <param><string>c</string></param>
            <param><string>d</string></param>
        </params>''')
        params = xmlrpc.encode_parameters('a', 'b', 'c', 'd').strip()
        params = re.sub(r'\s+', '', params)
        self.assertEqual(params, params_shouldbe)
    def test_encode_params_list(self):
        params_shouldbe = re.sub(r'\s+', '', '''
        <params>
            <param>
                <array>
                    <data>
                        <value><int>1</int></value>
                        <value><int>2</int></value>
                        <value><int>300</int></value>
                    </data>
                </array>
            </param>
        </params>''')
        params = re.sub(r'\s+', '', xmlrpc.encode_parameters([1, 2, 300]))
        self.assertEqual(params, params_shouldbe)

    def test_encode_struct(self):
        structval = { 'a':1, 'b':[1, 2, 3], 'c':'cee'}
        structxml = re.sub(r'\s+', '', '''
        <params>
            <param>
                <struct>
                    <member>
                        <name>a</name>
                        <value><int>1</int></value>
                    </member>
                    <member>
                        <name>b</name>
                        <value><array>
                            <data>
                                <value><int>1</int></value>
                                <value><int>2</int></value>
                                <value><int>3</int></value>
                            </data>
                        </array></value>
                    </member>
                    <member>
                        <name>c</name>
                        <value><string>cee</string></value>
                    </member>
                </struct>
            </param>
        </params>''')

        params = re.sub(r'\s+', '', xmlrpc.encode_parameters(structval))
        self.assertEqual(params, structxml)

if __name__ == '__main__':
    unittest.main()
