'''
Created on Jan 14, 2015

@author: itpp
'''
from lxml import etree
from owslib.coverage.wcs200 import WebCoverageService_2_0_0 as wcs
from owslib.coverage.wcs200 import log as wcs_log
from owslib.coverage.wcs200 import WCS_names
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
        times = [GMLTimePosition.from_xml(child) for child in content]
        return cls(times)


class GMLBoundedBy(object):
    @classmethod
    def from_xml(cls, element):
        # This is a dumb class which just returns its only child (this is removed
        # from the spec in later revisions, but is still in place on the test server).
        return GMLEnvelope.from_xml(element[0])


def _GetCoverage_etree(coverage, fields=None, subsets=None,
                       result_format='NetCDF3'):
    """
    Construct an etree xml representation for a GetCoverage call.

    Args:
    * coverage (string):  (?? or CoverageDescription objects ??)
        which coverage to get
    * fields ((list of) string):  (?? or Field objects ???):
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
        raise ValueError(
           'All-fields operation (fields==None) not yet supported: '
           'Please specify a field or fields.')
    if isinstance(fields, basestring):  #TODO: or Field type
        fields = [fields]
    field_names = [fld if isinstance(fld, basestring) else fld.name
                   for fld in fields]

    if subsets is not None:
        raise ValueError('Fields subsetting not yet supported.')

    # Create a root GetCoverage element.
    # Make a dictionary with all our required namespaces.
    namespaces = {
        'wcs20': WCS_names['wcs20'],
        'rsub': 'http://www.opengis.net/wcs/range-subsetting/1.0',
        'srvx': 'http://www.opengis.net/wcs_service-extension_crs/1.0'}
    # NOTE: we define all the required namespaces at the top element.
    # This is a horrible cludge, to get around a server problem where it won't
    # recognise an element in a namespace defined within the same element
    # (even though that is perfectly good XML practice).
    tagname = '{{{wcs20}}}GetCoverage'.format(**namespaces)
    root_el = etree.Element(tagname, service='WCS', version='2.0.0',
                            nsmap=namespaces)

    # Add a 'root_el/Extension' element.
    tagname = '{{{wcs20}}}Extension'.format(**namespaces)
    ext_el = etree.SubElement(root_el, tagname)

    # Add a root_el/Extension/RangeSubset, specifying the fields required.
    tagname = '{{{rsub}}}rangeSubset'.format(**namespaces)
    subs_el = etree.SubElement(ext_el, tagname)
    for fld_name in field_names:
        tagname = ('{{{rsub}}}rangeComponent'.format(**namespaces))
        fld_el = etree.Element(tagname)
        fld_el.text = fld_name
        subs_el.append(fld_el)

    # Add a root_el/Extension/GetCoverageCrs
    tagname = '{{{srvx}}}GetCoverageCrs'.format(**namespaces)
    crs_el = etree.SubElement(ext_el, tagname)
    # Add a root_el/Extension/GetCoverageCrs/subsettingCrs
    # N.B. the server insists on having one, but it can be empty.
    # This presumably means access in the native CRS.
    tagname = '{{{srvx}}}subsettingCrs'.format(**namespaces)
    crs_ss_el = etree.SubElement(crs_el, tagname)

    # Add the root/coverageId element.
    tagname = '{{{wcs20}}}CoverageId'.format(**namespaces)
    cov_el = etree.SubElement(root_el, tagname)
    cov_el.text = coverage_string

    # Add the root/format element.
    tagname = '{{{wcs20}}}format'.format(**namespaces)
    fmt_el = etree.SubElement(root_el, tagname)
    fmt_el.text = result_format

    return root_el


def GetCoverage_xml(*args, **kwargs):
    """
    Return xml for a GetCoverage call.

    Args:
    * coverage (string):  (?? or CoverageDescription objects ??)
        which coverage to get
    * fields ((list of) string):  (?? or Field objects ???):
        which fields (aka phenomenon names).  (Default is all).
    * subsets (list of ???):
        specify dimension subsetting
    * result_format (string):
        type of file to return.

    """
    tree = _GetCoverage_etree(*args, **kwargs)
    text = etree.tostring(tree, xml_declaration=True, encoding='UTF-8')
    return text


def GetCoverage(*args, **kwargs):
    """
    Return xml for a GetCoverage call.

    Args:
    * coverage (string):  (?? or CoverageDescription objects ??)
        which coverage to get
    * fields ((list of) string):  (?? or Field objects ???):
        which fields (aka phenomenon names).  (Default is all).
    * subsets (list of ???):
        specify dimension subsetting
    * result_format (string):
        type of file to return.

    """
    tree = _GetCoverage_etree(*args, **kwargs)
    text = etree.tostring(tree, xml_declaration=True, encoding='UTF-8')
    return text


def register_wcs_extension_subtypes():
    for cls in _WCS_EXTENSION_SUBTYPES:
        wcs.recognised_capability_extensions[cls.TAG] = cls
