#from __future__ import print_function
import lxml
import warnings

namespaces = {'gml': 'http://www.opengis.net/gml/3.2',
              'gmlrgrid': 'http://www.opengis.net/gml/3.3/rgrid'}


class GeometryTypeTracking(type):
    """
    A metaclass to keep track of any abstract geometry subclasses.
    """
    def __init__(cls, name, bases, dct):
        # Update the _geometry_types dictionary for any subclass which
        # is created.
        for tag in cls.TAGS or []:
            cls._geometry_types[tag] = cls

        super(GeometryTypeTracking, cls).__init__(name, bases, dct)


def apply_namespace(tag, namespaces):
    for key, namespace in namespaces.items():
        tag = tag.replace(key + ':', '{' + namespace + '}')
    return tag

def de_namespace(tag, namespaces):
    for key, namespace in namespaces.items():
        tag = tag.replace('{' + namespace + '}', key + ':')
    return tag


def non_instantiable(cls):
    def __init__(self, *args, **kwargs):
        raise ValueError('The {} class cannot be created - it is a simple XML container.')
    cls.__init__ = __init__
    return cls


@non_instantiable
class GMLConcept(object):
    #: The GML tags where this GML concept can be found.
    TAGS = None

    @classmethod
    def from_xml(cls, element):
        return cls(**cls.init_kwargs_from_xml(element))

    def __repr__(self):
        return '<{} instance>'.format(self.__class__.__name__)

    @classmethod
    def find(cls, parent_element, allow_none=True):
        """Find a single XML element which can be used by this GML concept."""
        element = None
        for tag in cls.TAGS or []:
            element = parent_element.find(tag, namespaces=namespaces)
            if element is not None:
                break
        if element is None and not allow_none:
            raise ValueError('Tags {} not found.'.format(', '.join(cls.TAGS or [])))
        return element

    @classmethod
    def find_one(cls, parent_element):
        return cls.find(parent_element, allow_none=False)


class GMLAbstractGeometry(GMLConcept):
    # Ref: 10.1.3.1 AbstractGeometryType
    __metaclass__ = GeometryTypeTracking

    #: The GML tags that this geometry represents.
    TAGS = None

    #: A mapping of GML tag to concrete implementation.
    #: This is updated automatically upon subclassing GMLAbstractGeometry
    #: and defining a suitable TAG class attribute.
    _geometry_types = {}

    @classmethod
    def subclass_from_xml(cls, element):
        geometry_class = cls._geometry_types[de_namespace(element.tag, namespaces)]
        return geometry_class.from_xml(element)


class GMLdomainSet(GMLConcept):
    # Ref: 19.3.4 domainSet, DomainSetType
    TAGS = ['gml:domainSet']

    @classmethod
    def from_xml(cls, element):
        geometry = GMLAbstractGeometry.subclass_from_xml(element[0])
        return geometry


class GMLPoint(GMLAbstractGeometry):
    # See 10.3.1 PointType, Point
    TAGS = ['gml:Point']
    def __init__(self, xy):
        self.xy = xy

    @classmethod
    def from_xml(cls, element):
        coords = element.find('gml:coordinates', namespaces=namespaces).text.split()
        coords = [float(val) for val in coords]
        if not coords and element.find('gml:pos'):
            raise NotImplementedError('gml:pos not implemented yet. Very simple!')
        return cls(coords)

    def __repr__(self):
        return 'GMLPoint({})'.format(self.xy)


class GMLGrid(GMLAbstractGeometry):
    # See 19.2.2 Grid
    TAGS = ['gml:Grid']
    def __init__(self, limits, axes, dims):
        self.limits, self.axes, self.dims = limits, axes, dims

    @classmethod
    def init_kwargs_from_xml(cls, element):
        limits = GMLGridEnvelope.from_xml(element.find('gml:limits', namespaces=namespaces)[0])

        axes = [axis.text for axis in element.findall('gml:axisName', namespaces=namespaces)]
        labels = element.find('gml:axisLabels', namespaces=namespaces)
        if not axes and labels is not None:
            axes = labels.text.split()

        dims = int(element.get('dimension'))
        return {'limits': limits, 'axes': axes, 'dims': dims}


class GMLRectifiedGrid(GMLGrid):
    # See 19.2.3 RectifiedGrid
    TAGS = ['gml:RectifiedGrid']

    def __init__(self, limits, axes, dims, origin, offset_vectors):
        super(GMLRectifiedGrid, self).__init__(limits, axes, dims)
        self.origin, self.offset_vectors = origin, offset_vectors

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = GMLGrid.init_kwargs_from_xml(element)

        origin_element = element.find('gml:origin', namespaces=namespaces)[0]
        origin = GMLAbstractGeometry.subclass_from_xml(origin_element)

        offset_vectors = [GMLVector.from_xml(vector)
                          for vector in element.findall('gml:offsetVector', namespaces=namespaces)]

        kwargs.update({'offset_vectors': offset_vectors, 'origin': origin})
        return kwargs


class AbstractReferenceableGrid(GMLGrid):
    # See 10.3 AbstractReferenceableGrid
    pass


class GMLReferenceableGridByArray(AbstractReferenceableGrid):
    # See 10.4 ReferenceableGridByArray
    TAGS = ['gml:ReferencableGridByArray',
            'gmlrgrid:ReferencableGridByArray']
    def __init__(self, limits, axes, dims, pos_list, sequence_rule):
        super(GMLReferenceableGridByArray, self).__init__(limits, axes, dims)
        self.pos_list = pos_list
        self.sequence_rule = sequence_rule

    def np_arrays(self):
        import numpy as np
        assert self.sequence_rule[1] == 'Linear'
        axes_dims = [int(dim[1:]) - 1 for dim in self.sequence_rule[0].split(' ')]
        values = np.array(self.pos_list)
        axes_arrays = {ax: values[ax_i::len(self.axes)] for ax_i, ax in enumerate(self.axes)}

        shape = self.limits.highs
        if np.prod(shape) != len(axes_arrays.values()[0]):
            # There are some badly implemented GridEnvelopes out there...
            n_unique = {ax: len(np.unique(arr)) for ax, arr in axes_arrays.items()}
            shape = [n_unique[ax] for ax in self.axes]

        for ax_name, axes_dim in zip(axes_arrays, axes_dims):
            # XXX Completely undocumented, but it looks to be column-major order...
            axes_arrays[ax_name] = axes_arrays[ax_name].reshape(shape, order='f')

            # Let's tidy up and remove the repeated dimension (leaving that dimension length one).
            full = [slice(0, 1)] * len(shape)
            full[axes_dim] = slice(None)
            axes_arrays[ax_name] = axes_arrays[ax_name][full]

        return axes_arrays

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = AbstractReferenceableGrid.init_kwargs_from_xml(element)

        pos_list = GMLPosList.from_xml(GMLPosList.find_one(element))

        sequence_rule = GMLSequenceRule.find_one(element)
        sequence_rule = sequence_rule.get('axisOrder'), sequence_rule.text
        kwargs.update({'pos_list': pos_list, 'sequence_rule': sequence_rule})
        return kwargs


class GMLSequenceRule(GMLConcept):
    TAGS = ['gml:sequenceRule', 'gmlrgrid:sequenceRule']


class GMLEnvelope(GMLConcept):
    # See 10.1.4.6 EnvelopeType, Envelope
    def __init__(self, lows, highs):
        self.lows, self.highs = lows, highs

    @classmethod
    def from_xml(cls, element):
        lows = element.find('gml:lowerCorner', namespaces=namespaces).text.split()
        highs = element.find('gml:upperCorner', namespaces=namespaces).text.split()
        lows = map(float, lows)
        highs = map(float, highs)
        return cls(lows, highs)

    def __repr__(self):
        return 'GMLEnvelope(lows={}, highs={})'.format(self.lows, self.highs)


class GMLGridEnvelope(GMLConcept):
    # See 10.1.4.6 EnvelopeType, Envelope
    def __init__(self, lows, highs):
        self.lows, self.highs = lows, highs

    @classmethod
    def from_xml(cls, element):
        # Note: This is not always 2 dimensional!
        lows = element.find('gml:low', namespaces=namespaces).text.split()
        highs = element.find('gml:high', namespaces=namespaces).text.split()
        return cls(map(int, lows), map(int, highs))

    def __repr__(self):
        return 'GMLGridEnvelope(lows={}, highs={})'.format(self.lows, self.highs)



class GMLVector(GMLConcept):
    # See 10.1.4.5 VectorType, Vector
    def __init__(self, components):
        self.components = components

    @classmethod
    def from_xml(cls, element):
        components = [float(val) for val in element.text.split()]
        return cls(components)

    def __repr__(self):
        return 'GMLVector({})'.format(self.components)


class GMLPosList(GMLConcept):
    # See 10.1.4.2 DirectPositionListType, posList
    TAGS = ['gml:posList']

    @classmethod
    def from_xml(cls, element):
        values = map(float, element.text.split())
        return values

# Chapter 14

GMLTimeFormat = '%Y-%m-%dT%H:%M:%SZ'


class GMLTimePosition(GMLConcept):
    # See 14.2.2.7 TimePositionType, timePosition
    def __init__(self, datetime):
        self.datetime = datetime

    @classmethod
    def from_xml(cls, element):
        from datetime import datetime
        dt = datetime.strptime(element.text, GMLTimeFormat)
        return cls(dt)

    def __repr__(self):
        return 'GMLTimePosition({!r})'.format(self.datetime)


class GMLTimePeriod(GMLConcept):
    # 14.2.2.5 TimePeriod
    def __init__(self, start, end):
        self.start = start
        self.end = end

    @classmethod
    def from_xml(cls, element):
        start = element.find('gml:beginPosition', namespaces=namespaces)
        if start is None:
            raise ValueError('End position not found. gml:start needs to be implemented.')
#            start = element.find('gml:begin', namespaces=namespaces)

        end = element.find('gml:endPosition', namespaces=namespaces)
        if end is None:
            raise ValueError('End position not found. gml:end needs to be implemented.')
#            end = element.find('gml:end', namespaces=namespaces)

        from datetime import datetime
        start = datetime.strptime(start.text, GMLTimeFormat)
        end = datetime.strptime(end.text, GMLTimeFormat)

        return cls(start, end)
    
    def __repr__(self):
        return 'TimePeriod({!r}, {!r})'.format(self.start, self.end)

# Chapter 19

class GMLRangeSet(GMLConcept):
    # See 19.3.5 rangeSet, RangeSetType
    def __init__(self, data):
        self.data = data

    @classmethod
    def from_xml(cls, element):
        data = GMLDataBlock.from_xml(element.find('gml:DataBlock', namespaces=namespaces))
        parameters = element.find('gml:rangeParameters', namespaces=namespaces)
        if parameters is not None:
            raise NotImplementedError('Range parameters not yet implemented in gml:RangeSet.')
        return cls(data)


class GMLDataBlock(GMLConcept):
    # See 19.3.6 DataBlock
    def __init__(self, values):
        self.values = values

    @classmethod
    def from_xml(cls, element):
        components = element.find('gml:tupleList', namespaces=namespaces).text.split(',')
        values = [component.split() for component in components]
        return cls(values)






#def de_namelist(element):
#    """
#    Convert a namelist to a real list.
#    
#    See 8.2.4.1 booleanList, doubleList, integerList, NameList, NCNameList, QNameList,
#                booleanOrNilReasonList, NameOrNilReasonList, doubleOrNilReasonList,
#                integerOrNilReasonList
#
#    """


if __name__ == '__main__':
    from lxml import etree

    with open('describeCoverage_met_ocean_example.txt', 'r') as fh:
        root = etree.XML(fh.read())

    import gmlcov
    import wcs_20_describe_coverage as wcs
    import wcs_20_metocean

    coverage = wcs.DescribeCoverage.from_xml(root[0])
    print type(coverage.extension)
    data_mask = coverage.extension.fields['relative-humidity']
    ds = data_mask.grid_coverage.domain_set

#    print ds.np_arrays()