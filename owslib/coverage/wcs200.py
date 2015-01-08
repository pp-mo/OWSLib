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

from wcsBase import WCSBase, WCSCapabilitiesReader, ServiceException
from owslib.util import openURL, testXMLValue
from urllib import urlencode
from urllib2 import urlopen
from owslib.etree import etree
import os, errno
from owslib.coverage import wcsdecoder
from owslib.crs import Crs

import logging
from owslib.util import log

from owslib.etree import etree

def ns(tag):
    return '{http://www.opengis.net/wcs/2.0}'+tag

from owslib.namespaces import Namespaces
from owslib.util import nspath_eval

WCS_namespaces = Namespaces().get_namespaces(['wcs', 'wcs20', 'ows', 'ows200'])
WCS_namespaces['wcs20ows'] = WCS_namespaces['wcs20'] + '/ows'


VERSION = '2.0.0'


def find_element(document, name, namespaces):
    """
    Find an element in a document given some possible namespaces.
    
    e.g. find_element(capabilities, 'ServiceIdentification', ['ows200', 'wcs200ows'])
    """
    if isinstance(namespaces, basestring):
        namespaces = [namespaces]
    for ns in namespaces:
        elem = document.find('{}:{}'.format(ns, name), namespaces=WCS_namespaces)
        if elem is not None:
            return elem
    raise ValueError('Element {} not found.'.format(name))


class WCSExtension(object):
    def __init__(self):
        pass
    
    @classmethod
    def from_xml(cls, element, service):
        """
        Given the XML dom object, and the service from whence it came,
        construct an extension instance.
        """
        raise NotImplementedError()

    registered_extensions = {}


class MetOceanCoverageCollection(WCSExtension):
    WCS_namespaces['WCSmetOcean'] = 'http://def.wmo.int/metce/2013/metocean'

    def __init__(self, service, coverage_collection_id, envelope=None, reference_times=None):
        #: The WebCoverageService instance that created this CoverageCollection.
        self.service = service

        self.coverage_collection_id = coverage_collection_id
        self.envelope = envelope
        self.reference_times = reference_times

    @classmethod
    def from_xml(cls, element, service):
        get_text = lambda elem: elem.text
        element_mapping = {'{{{WCSmetOcean}}}coverageCollectionId'.format(**WCS_namespaces): ['coverage_collection_id', get_text],
                           # The latest spect states that there will be an envelope at this level, but the test server has a boundedBy parenting the envelope.
                           '{{{gml32}}}boundedBy'.format(**WCS_namespaces): ['envelope', GMLBoundedBy.from_xml],
                           '{{{WCSmetOcean}}}referenceTimeList'.format(**WCS_namespaces): ['reference_times', ReferenceTimes.from_xml]}
        keywords = {'service': service}
        for child in element:
            if child.tag in element_mapping:
                keyword_name, element_fn = element_mapping[child.tag]
                keywords[keyword_name] = element_fn(child)
            else:
                log.debug('Coverage tag {} not found.'.format(child.tag))
        try:
            return cls(**keywords)
        except:
            print('Tried to initialise {} with {}'.format(cls, keywords))
            raise

    def describe(self):
        """
        Request describeCoverageCollection for this collection.

        """
        service = self.service
        coverage_collection = self.service.find_operation('DescribeCoverageCollection')
        base_url = coverage_collection.href_via('HTTP', 'Get')

        #process kwargs
        request = {'version': service.version,
                   'request': 'DescribeCoverageCollection',
                   'service':'WCS',
                   '{{{WCSmetOcean}}}coverageCollectionId'.format(**WCS_namespaces): self.coverage_collection_id}
        #encode and request
        data = urlencode(request)

        return openURL(base_url, data, 'Get', service.cookies)

# Register the MetOcean extension.
WCSExtension.registered_extensions['{http://def.wmo.int/metce/2013/metocean}CoverageCollectionSummary'] = MetOceanCoverageCollection.from_xml


class ReferenceTimes(object):
    def __init__(self, times):
        self.times = times

    @classmethod
    def from_xml(cls, element):
        # XXX TODO
        return cls(element)


class GMLEnvelope(object):
    WCS_namespaces['gml32'] = "http://www.opengis.net/gml/3.2"
    def __init__(self, times):
        self.times = times

    @classmethod
    def from_xml(cls, element):
        # XXX TODO
        return cls(element)


class GMLBoundedBy(object):
    @classmethod
    def from_xml(cls, element):
        # This is a dumb class which just returns its only child (this is removed
        # from the spec in later revisions, but is still in place on the test server).
        return GMLEnvelope.from_xml(element[0])


class CoverageSummary(object):
    def __init__(self, coverageid, subtype=None):
        self.coverageid = coverageid
        self.subtype = subtype

    @classmethod
    def from_xml(cls, element):
        keywords = {'coverageid': '{{{wcs20}}}CoverageId'.format(**WCS_namespaces),
                    'subtype': '{{{wcs20}}}CoverageSubtype'.format(**WCS_namespaces)}
        element_mapping = {identifier: keyword_name
                           for keyword_name, identifier in keywords.items()}
        for child in element:
            if child.tag in element_mapping:
                keywords[element_mapping[child.tag]] = child.text
            else:
                log.debug('Coverage tag {} not found.'.format(child.tag))
        return cls(**keywords)


class WebCoverageService_2_0_0(WCSBase):
    """Abstraction for OGC Web Coverage Service (WCS), version 2.0.0
    Implements IWebCoverageService.

    """
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

        # initialize from saved capability document or access the server
        reader = WCSCapabilitiesReader(self.version)

        if xml:
            self._capabilities = reader.readString(xml)
        else:
            self._capabilities = reader.read(self.url)

        # check for exceptions
        se = self._capabilities.find('wcs20:Exception', namespaces=WCS_namespaces)

        if se is not None:
            err_message = str(se.text).strip()
            raise ServiceException(err_message, xml)

        #build metadata objects:
        #serviceIdentification metadata
        print(etree.tostring(self._capabilities, encoding='utf8', method='xml'))
        service = find_element(self._capabilities, 'ServiceIdentification',
                               ['ows200', 'wcs20ows', 'wcs20'])
        self.identification=ServiceIdentification(service)

        #serviceProvider
        try:
            provider = find_element(self._capabilities, 'ServiceProvider',
                                    ['ows200'])
        except ValueError:
            log.debug('WCS 2.0.0 DEBUG: No service provider identified.')
        else:
            self.provider = ServiceProvider(provider)

        #serviceOperations
        self.operations = []
        for operation in self._capabilities.find('ows200:OperationsMetadata',
                                                 namespaces=WCS_namespaces):
            self.operations.append(Operation(operation))

        contents = self._capabilities.find('wcs20:Contents', namespaces=WCS_namespaces)

        self.contents = {}
        for coverage in contents.findall('wcs20:CoverageSummary', namespaces=WCS_namespaces):
            coverage = CoverageSummary.from_xml(coverage)
            self.contents[coverage.coverageid] = coverage

        self.contents_extensions = []
        for content_extensions in contents.findall('wcs20:Extension', namespaces=WCS_namespaces):
            for extension in content_extensions:
                if extension.tag not in WCSExtension.registered_extensions:
                    print('FAIL:', extension.tag)
                    log.debug('Unsupported content extension: {}'.format(extension.tag))
                else:
                    extension = WCSExtension.registered_extensions[extension.tag](extension, self)
                    self.contents_extensions.append(extension)

    def items(self):
        return self.contents.items()

#    def describeCoverageCollection(self, collectionid):
#        if isinstance(collectionid, CoverageSummary):
#            collectionid = collectionid.collectionid

    #TO DO: Handle rest of the  WCS 1.1.0 keyword parameters e.g. GridCRS etc. 
    def getCoverage(self, identifier=None, bbox=None, time=None, format = None, store=False, rangesubset=None, gridbaseCRS=None, gridtype=None, gridCS=None, gridorigin=None, gridoffsets=None, method='Get',**kwargs):
        """Request and return a coverage from the WCS as a file-like object
        note: additional **kwargs helps with multi-version implementation
        core keyword arguments should be supported cross version
        example:
        cvg=wcs.getCoverageRequest(identifier=['TuMYrRQ4'], time=['2792-06-01T00:00:00.0'], bbox=(-112,36,-106,41),format='application/netcdf', store='true')

        is equivalent to:
        http://myhost/mywcs?SERVICE=WCS&REQUEST=GetCoverage&IDENTIFIER=TuMYrRQ4&VERSION=1.1.0&BOUNDINGBOX=-180,-90,180,90&TIMESEQUENCE=2792-06-01T00:00:00.0&FORMAT=application/netcdf
        
        if store = true, returns a coverages XML file
        if store = false, returns a multipart mime
        """
        if log.isEnabledFor(logging.DEBUG):
            log.debug('WCS 1.1.0 DEBUG: Parameters passed to GetCoverage: identifier=%s, bbox=%s, time=%s, format=%s, rangesubset=%s, gridbaseCRS=%s, gridtype=%s, gridCS=%s, gridorigin=%s, gridoffsets=%s, method=%s, other_arguments=%s'%(identifier, bbox, time, format, rangesubset, gridbaseCRS, gridtype, gridCS, gridorigin, gridoffsets, method, str(kwargs)))
        
        if method == 'Get':
            method='{http://www.opengis.net/wcs/1.1/ows}Get'
        try:
            base_url = next((m.get('url') for m in self.getOperationByName('GetCoverage').methods if m.get('type').lower() == method.lower()))
        except StopIteration:
            base_url = self.url


        #process kwargs
        request = {'version': self.version, 'request': 'GetCoverage', 'service':'WCS'}
        assert len(identifier) > 0
        request['identifier']=identifier
        #request['identifier'] = ','.join(identifier)
        if bbox:
            request['boundingbox']=','.join([repr(x) for x in bbox])
        if time:
            request['timesequence']=','.join(time)
        request['format']=format
        request['store']=store
        
        #rangesubset: untested - require a server implementation
        if rangesubset:
            request['RangeSubset']=rangesubset
        
        #GridCRS structure: untested - require a server implementation
        if gridbaseCRS:
            request['gridbaseCRS']=gridbaseCRS
        if gridtype:
            request['gridtype']=gridtype
        if gridCS:
            request['gridCS']=gridCS
        if gridorigin:
            request['gridorigin']=gridorigin
        if gridoffsets:
            request['gridoffsets']=gridoffsets

       #anything else e.g. vendor specific parameters must go through kwargs
        if kwargs:
            for kw in kwargs:
                request[kw]=kwargs[kw]

        #encode and request
        data = urlencode(request)

        u=openURL(base_url, data, method, self.cookies)
        return u

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
        self.formatOptions = [f.text for f in elem.findall('wcs20ows:Parameter/wcs20ows:AllowedValues/wcs20ows:Value',
                                                           namespaces=WCS_namespaces)]
        methods = []
        for verb in elem.findall('ows200:DCP/ows200:HTTP/*', namespaces=WCS_namespaces):
            url = verb.attrib['{http://www.w3.org/1999/xlink}href']
            methods.append((verb.tag, {'url': url}))
        self.methods = dict(methods)

    def __repr__(self):
        return repr(self.methods)

    def href_via(self, protocol='HTTP', method='Get'):
        if protocol != 'HTTP' or method not in ['Get', 'Post']:
            raise ValueError('Unexpected method or protocol.')
        for method, content in self.methods.items():
            if method.endswith(method):
                return content['url']


class ServiceIdentification(object):
    """ Abstraction for ServiceIdentification Metadata 
    implements IServiceIdentificationMetadata"""
    def __init__(self,elem):        
        self.service="WCS"
        self.version = VERSION
        self.title=testXMLValue(elem.find('{http://www.opengis.net/ows}Title'))
        if self.title is None:  #may have used the wcs ows namespace:
            self.title=testXMLValue(elem.find('{http://www.opengis.net/wcs/1.1/ows}Title'))
        
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


class ContentMetadata(object):
    """Abstraction for WCS ContentMetadata
    Implements IContentMetadata
    """
    def __init__(self, elem, parent, service):
        """Initialize."""
        #TODO - examine the parent for bounding box info.
        
        self._service=service
        self._elem=elem
        self._parent=parent
        self.id=self._checkChildAndParent('{http://www.opengis.net/wcs/1.1}Identifier')
        self.description =self._checkChildAndParent('{http://www.opengis.net/wcs/1.1}Description')           
        self.title =self._checkChildAndParent('{http://www.opengis.net/ows}Title')
        self.abstract =self._checkChildAndParent('{http://www.opengis.net/ows}Abstract')
        
        #keywords.
        self.keywords=[]
        for kw in elem.findall('{http://www.opengis.net/ows}Keywords/{http://www.opengis.net/ows}Keyword'):
            if kw is not None:
                self.keywords.append(kw.text)
        
        #also inherit any keywords from parent coverage summary (if there is one)
        if parent is not None:
            for kw in parent.findall('{http://www.opengis.net/ows}Keywords/{http://www.opengis.net/ows}Keyword'):
                if kw is not None:
                    self.keywords.append(kw.text)
            
        self.boundingBox=None #needed for iContentMetadata harmonisation
        self.boundingBoxWGS84 = None
        b = elem.find('{http://www.opengis.net/ows}WGS84BoundingBox')
        if b is not None:
            lc=b.find('{http://www.opengis.net/ows}LowerCorner').text
            uc=b.find('{http://www.opengis.net/ows}UpperCorner').text
            self.boundingBoxWGS84 = (
                    float(lc.split()[0]),float(lc.split()[1]),
                    float(uc.split()[0]), float(uc.split()[1]),
                    )
                
        # bboxes - other CRS 
        self.boundingboxes = []
        for bbox in elem.findall('{http://www.opengis.net/ows}BoundingBox'):
            if bbox is not None:
                try:
                    lc=b.find('{http://www.opengis.net/ows}LowerCorner').text
                    uc=b.find('{http://www.opengis.net/ows}UpperCorner').text
                    boundingBox =  (
                            float(lc.split()[0]),float(lc.split()[1]),
                            float(uc.split()[0]), float(uc.split()[1]),
                            b.attrib['crs'])
                    self.boundingboxes.append(boundingBox)
                except:
                     pass

        #others not used but needed for iContentMetadata harmonisation
        self.styles=None
        self.crsOptions=None
                
        #SupportedCRS
        self.supportedCRS=[]
        for crs in elem.findall('{http://www.opengis.net/wcs/1.1}SupportedCRS'):
            self.supportedCRS.append(Crs(crs.text))
            
            
        #SupportedFormats         
        self.supportedFormats=[]
        for format in elem.findall('{http://www.opengis.net/wcs/1.1}SupportedFormat'):
            self.supportedFormats.append(format.text)
            
    #grid is either a gml:Grid or a gml:RectifiedGrid if supplied as part of the DescribeCoverage response.
    def _getGrid(self):
        grid=None
        #TODO- convert this to 1.1 from 1.0
        #if not hasattr(self, 'descCov'):
                #self.descCov=self._service.getDescribeCoverage(self.id)
        #gridelem= self.descCov.find(ns('CoverageOffering/')+ns('domainSet/')+ns('spatialDomain/')+'{http://www.opengis.net/gml}RectifiedGrid')
        #if gridelem is not None:
            #grid=RectifiedGrid(gridelem)
        #else:
            #gridelem=self.descCov.find(ns('CoverageOffering/')+ns('domainSet/')+ns('spatialDomain/')+'{http://www.opengis.net/gml}Grid')
            #grid=Grid(gridelem)
        return grid
    grid=property(_getGrid, None)



if __name__ == '__main__':
    wcs = WebCoverageService_2_0_0('http://exxvmviswxaftsing02:8008/GlobalWCSService')
    print(wcs.contents)
    print(wcs.contents_extensions)
    print(wcs.operations)
    print(wcs.contents_extensions[0].describe().read())
