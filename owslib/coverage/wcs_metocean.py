'''
Created on Jan 14, 2015

@author: itpp
'''
from owslib.coverage.wcs200 import WebCoverageService_2_0_0 as wcs
from owslib.coverage.wcs200 import log as wcs_log
from owslib.coverage.gml import GMLTimePosition, GMLEnvelope

# Define useful namespace lookup dictionaries.
MO_names = {'meto': 'http://def.wmo.int/metce/2013/metocean'}
GML_names = {'gml32': 'http://www.opengis.net/gml/3.2'}

# A list of the subtypes of WCSExtension that we want to recognise.
_WCS_EXTENSION_SUBTYPES = []

class MetOceanCoverageCollection(object):
    # Define the XML tag that this object represents.
    TAG = '{http://def.wmo.int/metce/2013/metocean}CoverageCollectionSummary'

    def __init__(self, service, coverage_collection_id,
                 name=None, envelope=None, reference_times=None):
        #: The WebCoverageService instance that created this CoverageCollection.
        self.service = service

        self.name = name
        self.coverage_collection_id = coverage_collection_id
        self.envelope = envelope
        self.reference_times = reference_times

    @classmethod
    def from_xml(cls, element, service):
        get_text = lambda elem: elem.text
        element_mapping = {
            '{{{meto}}}coverageCollectionId'.format(**MO_names): ['coverage_collection_id', get_text],
            # The latest spect states that there will be an envelope at this level, but the test server has a boundedBy parenting the envelope.
            '{{{gml32}}}boundedBy'.format(**GML_names): ['envelope', GMLBoundedBy.from_xml],
            '{{{meto}}}referenceTimeList'.format(**MO_names): ['reference_times', MetOceanReferenceTimeList.from_xml],
            '{{{gml32}}}name'.format(**GML_names): ['name', get_text]
            }
        keywords = {'service': service}
        for child in element:
            if child.tag in element_mapping:
                keyword_name, element_fn = element_mapping[child.tag]
                keywords[keyword_name] = element_fn(child)
            else:
                wcs_log.debug('Coverage tag {} not found.'.format(child.tag))
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
                   '{{{meto}}}coverageCollectionId'.format(**MO_names): self.coverage_collection_id}
        #encode and request
        data = urlencode(request)

        return openURL(base_url, data, 'Get', service.cookies)

# Add this class to our list of Extension subtypes that we want WCS2.0 to recognise.
_WCS_EXTENSION_SUBTYPES.append(MetOceanCoverageCollection)


class MetOceanReferenceTimeList(object):
    def __init__(self, times):
        self.times = times

    @classmethod
    def from_xml(cls, element):
        #print('REFTIME-fromxml:', type(element), repr(element))
        content, = element.findall('meto:ReferenceTime', namespaces=MO_names)
        children = content.findall('gml32:timePosition', namespaces=GML_names)
        times = [GMLTimePosition(child) for child in content]
        return cls(times)


class GMLBoundedBy(object):
    @classmethod
    def from_xml(cls, element):
        # This is a dumb class which just returns its only child (this is removed
        # from the spec in later revisions, but is still in place on the test server).
        return GMLEnvelope.from_xml(element[0])


def register_wcs_extension_subtypes():
    for cls in _WCS_EXTENSION_SUBTYPES:
        wcs.recognised_capability_extensions[cls.TAG] = cls
