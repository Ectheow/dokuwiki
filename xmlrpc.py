import xml.etree.ElementTree as ET
import requests

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
    str:lambda s: '<string>{}</string>'.format(s),
    int:lambda i: '<int>{}</int>'.format(i),
    list:_encode_list,
    dict:_encode_struct,
    bool: lambda b: '<boolean>{}</boolean'.format(int(b))
}


def encode_parameters(*params):
    paramstr='<params>'
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

decoders = {
    'array':_decode_array,
    'string':_decode_string,
    'struct':_decode_struct,
    'int':_decode_int,
    'boolean':_decode_boolean,
}


def decode_parameters(raw_parameters):
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
            raise RuntimeError("key {} is not in decoders".format(parameter_type.tag))

        decoded.append(decoders[parameter_type.tag](parameter_type))

    return decoded


class XMLRPCClientError(RuntimeError):
    pass

class XMLRPCClient:
    XML_HEADER='<?xml version="1.0" encoding="utf8"?>'
    def __init__(self, url):
        self.url = url
        self.cookies = requests.cookies.RequestsCookieJar()

    def call(self, method_name, *params):
        method_text = XMLRPCClient.XML_HEADER + \
                    '<methodCall>' + \
                    '<methodName>' + method_name + '</methodName>' + \
                    encode_parameters(list(params)) + \
                    '</methodCall>'
        response = requests.post(self.url,
                                 data=method_text)
        if not response.ok:
            raise XMLRPCClientError('Bad return code from server: {}'.format(
                response.text))

        self.cookies.update(response.cookies)
        #print(response.text)
        elements = ET.fromstring(response.text)
        params = elements.findall('./params')
        if len(params) != 1:
            raise XMLRPCClientError('There should be exactly one parameter tag: {} {}'.format(
                params, response.text))

        return decode_parameters(params[0])
