# -*- coding: ISO-8859-15 -*-
# =============================================================================
# Copyright (c) 2004, 2006 Sean C. Gillies
# Copyright (c) 2007 STFC <http://www.stfc.ac.uk>
#
# Authors : 
#          Dominic Lowe <d.lowe@rl.ac.uk>
#
# Contact email: d.lowe@rl.ac.uk
# =============================================================================

##########NOTE: Does not conform to new interfaces yet #################

from __future__ import (absolute_import, division, print_function)

import warnings

from owslib.coverage.wcsBase import WCSBase, WCSCapabilitiesReader, ServiceException
from owslib.util import openURL, testXMLValue
from urllib import urlencode
from urllib2 import urlopen
import os, errno
from owslib.coverage import wcsdecoder
from owslib.crs import Crs

import lxml.etree as etree

import logging
from owslib.util import log

#class local_log(object):
#    def debug(self, string):
#        print('DEBUG: ', string)
##        if not string.startswith('WCS'):
##            raise Exception()
#
#log = local_log()

from owslib.etree import etree

def ns(tag):
    return '{http://www.opengis.net/wcs/2.0}'+tag

from owslib.namespaces import Namespaces
from owslib.util import nspath_eval

# Define useful namespace lookup dictionaries.
WCS_names = Namespaces().get_namespaces(['wcs', 'wcs20', 'ows', 'ows200'])
WCS_names['wcs20ows'] = WCS_names['wcs20'] + '/ows'

VERSION = '2.0.0'


def find_element(document, name, namespaces):
    """
    Find an element in a document with multiple aliases for its namespace.

    Args:

    * document (etree):
        An xml fragment.
    * name (string):
        A tagname to search for.
    * namespaces (string or list of string):
        A set of namespace aliasses.

    Return the first match using any of the given namespaces in WCS_names.

    For example:

        find_element(capabilities, 'ServiceIdentification',
                     ['ows200', 'wcs20ows'])

        This will match either:
        * 'http://www.opengis.net/ows/2.0:ServiceIdentification'
            (aka 'ows200:ServiceIdentification'), *or*
        *  'http://www.opengis.net/wcs/2.0/ows:ServiceIdentification'
            (aka 'wcs20ows:ServiceIdentification').

    """
    if isinstance(namespaces, basestring):
        namespaces = [namespaces]
    for ns in namespaces:
        elem = document.find('{}:{}'.format(ns, name), namespaces=WCS_names)
        if elem is not None:
            return elem
    raise ValueError('Element {} not found.'.format(name))


class CoverageSummary(object):
    def __init__(self, service, coverage_id, subtype=None):
        self.service = service
        self.coverage_id = coverage_id
        self.subtype = subtype

    @classmethod
    def from_xml(cls, element, service):
        keywords = {'coverage_id': '{{{wcs20}}}CoverageId'.format(**WCS_names),
                    'subtype': '{{{wcs20}}}CoverageSubtype'.format(**WCS_names)}
        element_mapping = {identifier: keyword_name
                           for keyword_name, identifier in keywords.items()}
        keywords['service'] = service
        for child in element:
            if child.tag in element_mapping:
                keywords[element_mapping[child.tag]] = child.text
            else:
                log.debug('Coverage tag {} not supported.'.format(child.tag))
        return cls(**keywords)
    
    def describe(self):
        """
        Request describeCoverage for this coverage.

        """
        service = self.service
        coverage_collection = self.service.find_operation('DescribeCoverage')
        base_url = coverage_collection.href_via('HTTP', 'Get')

        #process kwargs
        request = {'version': service.version,
                   'request': 'DescribeCoverage',
                   'service':'WCS',
                   'CoverageId': self.coverage_id}
        #encode and request
        data = urlencode(request)

        return openURL(base_url, data, 'Get', service.cookies)


class WebCoverageService_2_0_0(WCSBase):
    """Abstraction for OGC Web Coverage Service (WCS), version 2.0.0
    Implements IWebCoverageService.

    """
    # Define which concepts will be recognised within the Extension block of a
    # capabilities response.
    # This is a dictionary {<xml-tag>: <object-builder-class>}
    recognised_capability_extensions = {}

    def __getitem__(self, name):
        ''' check contents dictionary to allow dict like access to service layers'''
        if name in self.__getattribute__('contents').keys():
            return self.__getattribute__('contents')[name]
        else:
            raise KeyError("No content named %s" % name)

    def __new__(cls, url, xml=None, cookies=None):
        if cookies is not None:
            raise ValueError('WCS2 does not support cookies')
        return WCSBase.__new__(cls, url, xml, None)

    def __init__(self, url, xml=None, _=None):
        self.version = VERSION
        self.url = url

        def absent(name):
            log.debug('WCS 2.0.0 DEBUG: '
                      'capabilities contains no {} component.'.format(name))

        # initialize from saved capability document or access the server
        reader = WCSCapabilitiesReader(self.version)

        if xml:
            self._capabilities = reader.readString(xml)
        else:
            self._capabilities = reader.read(self.url)

        # check for exceptions
        se = self._capabilities.find('wcs20:Exception', namespaces=WCS_names)

        if se is not None:
            err_message = str(se.text).strip()
            raise ServiceException(err_message, xml)

        # build metadata objects

        # serviceIdentification metadata : may be absent
#         print(etree.tostring(self._capabilities, encoding='utf8', method='xml'))
        service = find_element(self._capabilities, 'ServiceIdentification',
                               ['ows200', 'wcs20ows', 'wcs20'])
        if service is None:
            self.identification = None
            absent('ServiceIdentification')
        else:
            self.identification = ServiceIdentification(service)

        # serviceProvider : may be absent.
        try:
            provider = find_element(self._capabilities, 'ServiceProvider',
                                    ['ows200'])
        except ValueError:
            self.provider = None
            absent('ServiceProvider')
        else:
            self.provider = ServiceProvider(provider)

        # serviceOperations : may be absent, else contains a list of Operation.
        operations = self._capabilities.find('ows200:OperationsMetadata',
                                             namespaces=WCS_names)
        if operations is None:
            self.operations = []
            absent('OperationsMetadata')
        else:
            self.operations = [Operation(operation)
                               for operation in operations]

        # contents : may be absent
        contents = self._capabilities.find('wcs20:Contents', namespaces=WCS_names)
        self.contents = {}
        self.contents_extensions = []
        if contents is None:
            absent('Contents')
        else:
            for coverage in contents.findall('wcs20:CoverageSummary', namespaces=WCS_names):
                coverage = CoverageSummary.from_xml(coverage, self)
                self.contents[coverage.coverage_id] = coverage

            # any extensions
            for content_extensions in contents.findall('wcs20:Extension', namespaces=WCS_names):
                for extension in content_extensions:
                    recognised_types = WebCoverageService_2_0_0.recognised_capability_extensions
                    if extension.tag not in recognised_types:
                        log.debug('Unsupported content extension : {}'.format(extension.tag))
                    else:
                        cls = recognised_types[extension.tag]
                        extension = cls.from_xml(extension, self)
                        self.contents_extensions.append(extension)

    def _raw_capabilities(self):
        return etree.tostring(self._capabilities, encoding='utf8', method='xml')

    def items(self):
        return self.contents.items()

#    def describeCoverageCollection(self, collectionid):
#        if isinstance(collectionid, CoverageSummary):
#            collectionid = collectionid.collectionid

    def _etree_for_GetCoverage(self, coverage, fields=None, subsets=None,
                            result_format='NetCDF3'):
        """
        Args:
        * coverage (string or CoverageSummary):
            which coverage to get
        * fields ((list of) string or ???):
            which fields (aka phenomenon names).  (Default is all).
        * subsets (list of ???):
            specify dimension subsetting
        * result_format (string):
            type of file to return.

        """
        if isinstance(coverage, basestring):
            coverage_string = coverage
        else:
            coverage_string = coverage.name
        if fields is None:
            fields = all_fields  # TODO: need to define this somehow !
        if isinstance(fields, basestring):  #TODO: or Field type
            fields = [fields]
        field_names = [fld if isinstance(fld, basestring) else fld.name
                       for fld in fields]
        # Create the root GetCoverage element.
        tagname = '{{{wcs20}}}GetCoverage'.format(**WCS_names)
        root_el = etree.Element(tagname,
                                service='WCS', version='2.0.0')

        # Add the absolutely minimal root_el/Extension element, as required.
        tagname = '{{{wcs20}}}Extension'.format(**WCS_names)
        ext_el = etree.SubElement(root_el, tagname)
        # Add a root_el/Extension/RangeSubset, specifying the fields required.
        tagname = ('{http://www.opengis.net/wcs/range-subsetting/1.0}'
                   'rangeSubset')
        subs_el = etree.SubElement(ext_el, tagname)
        for fld_name in field_names:
            tagname = ('{http://www.opengis.net/wcs/range-subsetting/1.0}'
                       'rangeComponent')
            fld_el = etree.Element(tagname)
            fld_el.text = fld_name
            subs_el.append(fld_el)
        # Add a root_el/Extension/GetCoverageCrs
        tagname = ('{http://www.opengis.net/wcs_service-extension_crs/1.0}'
                   'GetCoverageCrs')
        crs_el = etree.SubElement(ext_el, tagname)
        # Add a root_el/Extension/GetCoverageCrs/subsettingCrs
        tagname = ('{http://www.opengis.net/wcs_service-extension_crs/1.0}'
                   'subsettingCrs')
        crs_ss_el = etree.SubElement(crs_el, tagname)
        # N.B. insists on having one, and must have (at least) an empty text.
        crs_ss_el.text = ' \n '

        # Add the root/coverageId element.
        cov_el = etree.SubElement(root_el,
                               '{{{wcs20}}}CoverageId'.format(**WCS_names))
        cov_el.text = coverage_string

        # Add the format element.
        fmt_el = etree.SubElement(root_el,
                               '{{{wcs20}}}format'.format(**WCS_names))
        fmt_el.text = result_format
        return root_el

    def _xml_for_GetCoverage(self, *args, **kwargs):
        tree = self._etree_for_GetCoverage(*args, **kwargs)
        text = etree.tostring(tree)
        return '<?xml version="1.0" encoding="UTF-8"?>' + text

    def getCoverage(self, from_xml=None, **kwargs):
        if from_xml is None:
            from_xml = self._xml_for_GetCoverage(**kwargs)
        coverage_collection = self.find_operation('GetCoverage')
        base_url = coverage_collection.href_via('HTTP', 'Post')
        from owslib.util import http_post
        return http_post(base_url, from_xml)

    def getOperationByName(self, name):
        """Return a named operation item."""
        for item in self.operations:
            if item.name == name:
                return item
        raise KeyError("No operation named %s" % name)

    def find_operation(self, name):
        for item in self.operations:
            if item.name == name:
                return item
        raise KeyError("No operation named %s" % name)


class Operation(object):
    """Abstraction for operation metadata    
    Implements IOperationMetadata.
    """
    def __init__(self, elem):
        self.name = elem.get('name')
        self.formatOptions = [f.text for f in elem.findall(
            'wcs20ows:Parameter/wcs20ows:AllowedValues/wcs20ows:Value/ows200:AllowedValues',
            namespaces=WCS_names)]
        methods = []
        for verb in elem.findall('ows200:DCP/ows200:HTTP/*', namespaces=WCS_names):
            url = verb.attrib['{http://www.w3.org/1999/xlink}href']
            methods.append((verb.tag, {'url': url}))
        self.methods = dict(methods)

    def __repr__(self):
        return repr(self.methods)

    def href_via(self, protocol='HTTP', method='Get'):
        if protocol != 'HTTP' or method not in ['Get', 'Post']:
            raise ValueError('Unexpected method or protocol.')
        for method_type, content in self.methods.items():
            if method_type.endswith(method):
                return content['url']
        raise ValueError('{} method {} not found for {}.'.format(protocol, method, self.name))


class ServiceIdentification(object):
    """ Abstraction for ServiceIdentification Metadata 
    implements IServiceIdentificationMetadata"""
    def __init__(self,elem):        
        self.service="WCS"
        self.version = VERSION
        self.title=testXMLValue(elem.find('{http://www.opengis.net/ows}Title'))
        if self.title is None:  #may have used the wcs ows namespace:
            self.title=testXMLValue(elem.find('{http://www.opengis.net/wcs/1.1/ows}Title'))
        if self.title is None:  #may have used the ows200 namespace:
            self.title=testXMLValue(elem.find('{http://www.opengis.net/ows/2.0}Title'))
        
        self.abstract=testXMLValue(elem.find('{http://www.opengis.net/ows}Abstract'))
        if self.abstract is None:#may have used the wcs ows namespace:
            self.abstract=testXMLValue(elem.find('{http://www.opengis.net/wcs/1.1/ows}Abstract'))
        if elem.find('{http://www.opengis.net/ows}Abstract') is not None:
            self.abstract=elem.find('{http://www.opengis.net/ows}Abstract').text
        else:
            self.abstract = None
        self.keywords = [f.text for f in elem.findall('{http://www.opengis.net/ows}Keywords/{http://www.opengis.net/ows}Keyword')]
        #self.link = elem.find('{http://www.opengis.net/wcs/1.1}Service/{http://www.opengis.net/wcs/1.1}OnlineResource').attrib.get('{http://www.w3.org/1999/xlink}href', '')
               
        if elem.find('{http://www.opengis.net/wcs/1.1/ows}Fees') is not None:            
            self.fees=elem.find('{http://www.opengis.net/wcs/1.1/ows}Fees').text
        else:
            self.fees=None
        
        if  elem.find('{http://www.opengis.net/wcs/1.1/ows}AccessConstraints') is not None:
            self.accessConstraints=elem.find('{http://www.opengis.net/wcs/1.1/ows}AccessConstraints').text
        else:
            self.accessConstraints=None


class ServiceProvider(object):
    """ Abstraction for ServiceProvider metadata 
    implements IServiceProviderMetadata """
    def __init__(self,elem):
        name=elem.find('{http://www.opengis.net/ows}ProviderName')
        if name is not None:
            self.name=name.text
        else:
            self.name=None
        #self.contact=ServiceContact(elem.find('{http://www.opengis.net/ows}ServiceContact'))
        self.contact =ContactMetadata(elem)
        self.url=self.name # no obvious definitive place for url in wcs, repeat provider name?


class ContactMetadata(object):
    ''' implements IContactMetadata'''
    def __init__(self, elem):
        try:
            self.name = elem.find('{http://www.opengis.net/ows}ServiceContact/{http://www.opengis.net/ows}IndividualName').text
        except AttributeError:
            self.name = None
        
        try:
            self.organization=elem.find('{http://www.opengis.net/ows}ProviderName').text 
        except AttributeError:
            self.organization = None
        
        try:
            self.address = elem.find('{http://www.opengis.net/ows}ServiceContact/{http://www.opengis.net/ows}ContactInfo/{http://www.opengis.net/ows}Address/{http://www.opengis.net/ows}DeliveryPoint').text
        except AttributeError:
            self.address = None
        try:
            self.city=  elem.find('{http://www.opengis.net/ows}ServiceContact/{http://www.opengis.net/ows}ContactInfo/{http://www.opengis.net/ows}Address/{http://www.opengis.net/ows}City').text
        except AttributeError:
            self.city = None
        
        try:
            self.region= elem.find('{http://www.opengis.net/ows}ServiceContact/{http://www.opengis.net/ows}ContactInfo/{http://www.opengis.net/ows}Address/{http://www.opengis.net/ows}AdministrativeArea').text
        except AttributeError:
            self.region = None
        
        try:
            self.postcode= elem.find('{http://www.opengis.net/ows}ServiceContact/{http://www.opengis.net/ows}ContactInfo/{http://www.opengis.net/ows}Address/{http://www.opengis.net/ows}PostalCode').text
        except AttributeError:
            self.postcode = None
        
        try:
            self.country= elem.find('{http://www.opengis.net/ows}ServiceContact/{http://www.opengis.net/ows}ContactInfo/{http://www.opengis.net/ows}Address/{http://www.opengis.net/ows}Country').text
        except AttributeError:
            self.country = None
        
        try:
            self.email =            elem.find('{http://www.opengis.net/ows}ServiceContact/{http://www.opengis.net/ows}ContactInfo/{http://www.opengis.net/ows}Address/{http://www.opengis.net/ows}ElectronicMailAddress').text
        except AttributeError:
            self.email = None
