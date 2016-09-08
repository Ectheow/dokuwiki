import xml.etree.ElementTree as ET
import requests


'''
Module implementing basic XML RPC calls.

'''
def _encode_list(list_parameter):
    assert type(list_parameter) == list
    listr = '<array><data>'

    for elem in list_parameter:
        listr += '<value>' + \
                encoders[type(elem)](elem) + \
                '</value>'
    return listr + '</data></array>'

def _encode_struct(struct_parameter):
    assert type(struct_parameter) == dict
    structstr = '<struct>'
    for k in sorted(struct_parameter.keys()):
        v = struct_parameter[k]
        structstr += '<member>' + \
                     '<name>' + str(k) + '</name>' + \
                     '<value>' + \
                        encoders[type(v)](v) + \
                    '</value>' + \
                    '</member>'
    structstr += '</struct>'

    return structstr

def _encode_parameter(param):
    return '<param>' + \
            encoders[type(param)](param) + \
            '</param>'


encoders = {
    str:lambda s: '<string><![CDATA[{}]]></string>'.format(s),
    int:lambda i: '<int>{}</int>'.format(i),
    list:_encode_list,
    dict:_encode_struct,
    bool: lambda b: '<boolean>{}</boolean'.format(int(b))
}


def encode_parameters(*params):
    '''
    Encode parameters that are python data types into XML for an XMLRPC call.
    parameters may be dictionaries, lists, strings, integers, or booleans, and
    will be recursively encoded.

    *params -- parameters to be encoded into the params list.

    Returns: XML for an XML RPC call, starting with the <params> tag.

    ex:
    encode_parameters([1, 2, 3]) -->
    <params>
      <param>
        <array>
          <value><int>1</int></value>
          ...
        </array>
      </param>
    </params>
    '''
    paramstr='<params>'
    if params == [[]]:
        return ''

    for param in params:
        paramstr += _encode_parameter(param)

    return paramstr + '</params>'


def _decode_string(parameter):
    return str(parameter.text)

def _decode_array(parameter):
    parsed = []
    values = parameter.findall('./data')
    if len(values) != 1:
        raise RuntimeError('not enough or too many values: {} {}'.format(
            len(values), values))

    for value in values[0].findall('./value/*'):
        parsed.append(
            decoders[value.tag](value))

    return parsed


def _decode_struct(parameter):
    parsed = {}
    members = parameter.findall('./member')
    for member in members:
        names = member.findall('./name')
        if len(names) != 1:
            raise RuntimeError("not expected number of names: {} {}"
                    .format(len(names), names))

        name = names[0].text
        values = member.findall('./value/*')

        if len(values) != 1:
            raise RuntimeError('not expected number of struct member valuse: {} {}'
                    .format(len(values), values))

        parsed[name] = decoders[values[0].tag](values[0])

    return parsed

def _decode_boolean(parameter):
    return bool(int(parameter.text))

def _decode_int(parameter):
    return int(parameter.text)

def _decode_value(parameter):
    value = parameter.findall('./*')[0]
    return decoders[value.tag](value)

decoders = {
    'array':_decode_array,
    'string':_decode_string,
    'struct':_decode_struct,
    'int':_decode_int,
    'boolean':_decode_boolean,
    'value':_decode_value,
}


def decode_parameters(raw_parameters):
    '''
    Decode raw parameters from a methodResponse.

    raw_parameters -- either an XML string of the parameters, e.g.
                       <params>
                         <param>
                           ...
                         </param>
                       </params>
                       or an already parsed ElementTree.

    Returns: a python data type, a list, string int, dict, or boolean value.
    '''
    if type(raw_parameters) == str:
        root = ET.fromstring(raw_parameters)
    else:
        root = raw_parameters

    decoded = []
    parameters = root.findall('./param')
    for parameter in parameters:
        parameter_types = parameter.findall('./*')

        if not len(parameter_types) == 1:
            raise RuntimeError("too many elements in param: {} elements: {}".format(
                parameter.tag,
                parameter_types))

        parameter_type = parameter_types[0]

        if not parameter_type.tag in decoders:
            raise RuntimeError("key {} {} is not in decoders".format(parameter_type.tag, parameter_type.text))

        decoded.append(decoders[parameter_type.tag](parameter_type))

    return decoded


class XMLRPCClientError(RuntimeError):
    pass

class XMLRPCClientFaultError(RuntimeError):
    def __init__(self, fault_text, fault, params, request_xml):
        self._err_str = fault_text + '\nfault:\n' + \
                '\t' + 'code: ' + str(fault['faultCode']) + '\n' + \
                '\t' + 'message: ' + str(fault['faultString']) + '\n' + \
                '\t' + 'params: ' + '\n'
        for param in params:
            self._err_str += '\t\t' + str(param) + '\n'

        self._err_str += request_xml
        self._err_str += '\n'

    def __str__(self):
        return self._err_str

class XMLRPCClient:
    XML_HEADER='<?xml version="1.0" encoding="utf8"?>'
    def __init__(self, url, verify=True):
        '''
        url    -- url to send XML RPC POST requests to.
        verify -- whether or not to verify SSL certificates.
        '''
        self.url = url
        self.verify=verify
        self.cookies = requests.cookies.RequestsCookieJar()

    def call(self, method_name, *params):
        '''
        Call method method_name, returning whatever structure it returns,
        decoded. Throws an exception if:
            * HTTP return code isn't OK
            * The method resuponse doesn't have a <params> tag and <param> tags
            within.

        method_name -- method name to call
        *params     -- list of parameters to be encoded.
        '''
        method_text = XMLRPCClient.XML_HEADER + \
                    '<methodCall>' + \
                    '<methodName>' + method_name + '</methodName>' + \
                    (encode_parameters(*params) if len(params) > 0 else '') + \
                    '</methodCall>'
        response = requests.post(self.url,
                                 data=method_text,
                                 verify=self.verify,
                                 cookies=self.cookies)
        if not response.ok:
            raise XMLRPCClientError('Bad return code from server: {}'.format(
                response.text))

        self.cookies.update(response.cookies)
        elements = ET.fromstring(response.text.encode(encoding='ASCII', errors='ignore'))
        params = elements.findall('./params')
        if len(params) != 1:
            fault = elements.findall('./fault/value/struct')
            if len(fault) != 1:
                raise XMLRPCClientError('There should be exactly one parameter tag: {} {}'.format(
                    params, response.text))
            else:
                fault_dict = decoders[fault[0].tag](fault[0])
                raise XMLRPCClientFaultError('Fault calling ' + method_name,
                                             fault_dict,
                                             params,
                                             method_text)

        decoded = None
        try:
            decoded = decode_parameters(params[0])
        except RuntimeError as e:
            raise XMLRPCClientError("error with xml: {}, {}, {}".format(
                method_text, response.text, e))

        return decoded
