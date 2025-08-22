import requests
import traceback
import xml.dom.minidom
import os



eas_base_information = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Header/>
        <soapenv:Body>
            <sh:ShPull xmlns:sh="http://www.metaswitch.com/srb/soap/sh">
            <sh:UserIdentity>{tn}</sh:UserIdentity>
            <sh:DataReference>0</sh:DataReference>
            <sh:ServiceIndication>Msph_Subscriber_BaseInformation</sh:ServiceIndication>
            <sh:OriginHost>user@domain?clientVersion=8.0&amp;ignoreSequenceNumber=true</sh:OriginHost>
            </sh:ShPull>
        </soapenv:Body>
    </soapenv:Envelope>
"""


def send_soap(envelope, timeout=30, **kwargs):
    """
    Send a soap request to metaview soap server
    :param envelope: soap envelope
    :param timeout: timeout in seconds
    :param kwargs:
        - format: SOAP result will be pretty printed if True
    """
    headers = {'Content-Type': 'text/xml;charset=UTF-8',
               'SOAPAction': '""', 'Host': os.environ["MVS_SOAP_HOST"],
               'Connection': 'Keep-Alive'}
    r = requests.post(
        url=os.environ["MVS_SOAP_URL"],
        headers=headers,
        data=envelope.encode('utf-8'),
        timeout=timeout,
        auth=(os.environ["MVS_SOAP_USERNAME"], os.environ["MVS_SOAP_PASSWORD"]))
    r = r.text
    
    if 'format' in kwargs and kwargs['format']:
        try:
            dom = xml.dom.minidom.parseString(r)
            pretty_xml_as_string = dom.toprettyxml(indent="  ")
            r = pretty_xml_as_string
        except Exception as e:
            return r

    return r