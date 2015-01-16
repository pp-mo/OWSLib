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
        raise ValueError('The {} class cannot be created - it is a simple '
                         'XML container.'.format(self.__class__.__name__))
    cls.__init__ = __init__
    return cls


SRSInformationGroup_Attrs = ('axisLabels', 'uomLabels')
SRSReferenceGroup_Attrs = ('srsName', 'srsDimension') + SRSInformationGroup_Attrs


class GMLAbstractObject(object):
    pass


class GMLAbstractGML(GMLAbstractObject):
    #: The GML tags where this GML concept can be found.
    TAGS = []
    #: The possible tags that this GML concept could contain.
    ATTRS = ('gml:id', )

    def __init__(self, attrs):
        super(GMLAbstractObject, self).__init__()
        self.attrs = attrs

    @classmethod
    def init_kwargs_from_xml(cls, element):
        attrs = {}
        kwargs = {'attrs': attrs}

        for attr_name in cls.ATTRS:
            attr = element.get(apply_namespace(attr_name, namespaces))
            if attr is not None:
                attrs[attr_name] = attr
        return kwargs

    @classmethod
    def from_xml(cls, element):
        try:
            return cls(**cls.init_kwargs_from_xml(element))
        except TypeError:
            print cls
            print cls.init_kwargs_from_xml(element)
            print('Failed to construct a {} instance.'.format(cls))
            raise

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


class GMLAbstractGeometry(GMLAbstractGML):
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


class GMLdomainSet(GMLAbstractGML):
    # Ref: 19.3.4 domainSet, DomainSetType
    TAGS = ['gml:domainSet']

    @classmethod
    def from_xml(cls, element):
        geometry = GMLAbstractGeometry.subclass_from_xml(element[0])
        return geometry


class GMLPoint(GMLAbstractGeometry):
    # See 10.3.1 PointType, Point
    TAGS = ['gml:Point']
    def __init__(self, attrs, coords):
        super(GMLPoint, self).__init__(attrs)
        self.coords = coords

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLPoint, cls).init_kwargs_from_xml(element)

        coords = element.find('gml:coordinates', namespaces=namespaces).text.split()
        coords = [float(val) for val in coords]
        if not coords and element.find('gml:pos'):
            raise NotImplementedError('gml:pos not implemented yet. Very simple!')

        kwargs.update({'coords': coords})
        return kwargs

    def __repr__(self):
        return 'GMLPoint({!r}, {})'.format(self.attrs, self.coords)


class GMLGrid(GMLAbstractGeometry):
    # See 19.2.2 Grid
    TAGS = ['gml:Grid']
    def __init__(self, attrs, limits, axes, dims):
        super(GMLGrid, self).__init__(attrs)
        self.limits, self.axes, self.dims = limits, axes, dims

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLGrid, cls).init_kwargs_from_xml(element)

        limits = GMLGridEnvelope.from_xml(element.find('gml:limits', namespaces=namespaces)[0])

        axes = [axis.text for axis in element.findall('gml:axisName', namespaces=namespaces)]
        labels = element.find('gml:axisLabels', namespaces=namespaces)
        if not axes and labels is not None:
            axes = labels.text.split()

        dims = int(element.get('dimension'))

        kwargs.update({'limits': limits, 'axes': axes, 'dims': dims})
        return kwargs


class GMLRectifiedGrid(GMLGrid):
    # See 19.2.3 RectifiedGrid
    TAGS = ['gml:RectifiedGrid']

    def __init__(self, attrs, limits, axes, dims, origin, offset_vectors):
        super(GMLRectifiedGrid, self).__init__(attrs, limits, axes, dims)
        self.origin, self.offset_vectors = origin, offset_vectors

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLRectifiedGrid, cls).init_kwargs_from_xml(element)

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
    def __init__(self, attrs, limits, axes, dims, pos_list, sequence_rule):
        super(GMLReferenceableGridByArray, self).__init__(attrs, limits, axes, dims)
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
            if np.prod(shape) != len(axes_arrays.values()[0]):
                raise ValueError("Unable to determine the shapes of the grid arrays. "
                                 "The GridEnvelope should describe the number of points, but doesn't in this case.")

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
        kwargs = super(GMLReferenceableGridByArray, cls).init_kwargs_from_xml(element)

        pos_list = GMLPosList.from_xml(GMLPosList.find_one(element))

        sequence_rule = GMLSequenceRule.find_one(element)
        sequence_rule = sequence_rule.get('axisOrder'), sequence_rule.text

        kwargs.update({'pos_list': pos_list, 'sequence_rule': sequence_rule})
        return kwargs


class GMLSequenceRule(GMLAbstractGML):
    TAGS = ['gml:sequenceRule', 'gmlrgrid:sequenceRule']


class GMLEnvelope(GMLAbstractGML):
    # See 10.1.4.6 EnvelopeType, Envelope
    TAGS = ['gml:Envelope']
    ATTRS = GMLAbstractGML.ATTRS + SRSReferenceGroup_Attrs

    def __init__(self, attrs, lows, highs):
        super(GMLEnvelope, self).__init__(attrs)
        self.lows, self.highs = lows, highs

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLEnvelope, cls).init_kwargs_from_xml(element)

        lows = element.find('gml:lowerCorner', namespaces=namespaces).text.split()
        highs = element.find('gml:upperCorner', namespaces=namespaces).text.split()
        lows = map(float, lows)
        highs = map(float, highs)

        kwargs.update({'lows': lows, 'highs': highs})
        return kwargs

    def __repr__(self):
        return 'GMLEnvelope({!r}, lows={}, highs={})'.format(self.attrs, self.lows, self.highs)


class GMLGridEnvelope(GMLAbstractGML):
    # See 10.1.4.6 EnvelopeType, Envelope
    def __init__(self, attrs, lows, highs):
        super(GMLGridEnvelope, self).__init__(attrs)
        self.lows, self.highs = lows, highs

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLGridEnvelope, cls).init_kwargs_from_xml(element)

        # Note: This is not always 2 dimensional!
        lows = element.find('gml:low', namespaces=namespaces).text.split()
        highs = element.find('gml:high', namespaces=namespaces).text.split()

        kwargs.update({'lows': map(int, lows), 'highs': map(int, highs)})
        return kwargs

    def __repr__(self):
        return 'GMLGridEnvelope({!r}, lows={}, highs={})'.format(self.attrs, self.lows, self.highs)



class GMLVector(GMLAbstractGML):
    # See 10.1.4.5 VectorType, Vector
    def __init__(self, attrs, components):
        super(GMLVector, self).__init__(attrs)
        self.components = components

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLVector, cls).init_kwargs_from_xml(element)

        components = [float(val) for val in element.text.split()]

        kwargs.update({'components': components})
        return kwargs

    def __repr__(self):
        return 'GMLVector({!r}, {})'.format(self.attrs, self.components)


class GMLPosList(GMLAbstractGML):
    # See 10.1.4.2 DirectPositionListType, posList
    TAGS = ['gml:posList']

    @classmethod
    def from_xml(cls, element):
        values = map(float, element.text.split())
        return values

# Chapter 14

GMLTimeFormat = '%Y-%m-%dT%H:%M:%SZ'


class GMLTimePosition(GMLAbstractGML):
    # See 14.2.2.7 TimePositionType, timePosition
    def __init__(self, attrs, datetime):
        super(GMLTimePosition, self).__init__(attrs)
        self.datetime = datetime

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLTimePosition, cls).init_kwargs_from_xml(element)

        from datetime import datetime
        dt = datetime.strptime(element.text, GMLTimeFormat)

        kwargs.update({'datetime': dt})
        return kwargs

    def __repr__(self):
        return 'GMLTimePosition({!r}, {!r})'.format(self.attrs, self.datetime)


class GMLTimePeriod(GMLAbstractGML):
    # 14.2.2.5 TimePeriod
    def __init__(self, attrs, start, end):
        super(GMLTimePeriod, self).__init__(attrs)
        self.start = start
        self.end = end

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLTimePeriod, cls).init_kwargs_from_xml(element)

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

        kwargs.update({'start': start, 'end': end})
        return kwargs

    def __repr__(self):
        return 'TimePeriod({!r}, {!r}, {!r})'.format(self.attrs, self.start, self.end)

# Chapter 19

class GMLRangeSet(GMLAbstractGML):
    # See 19.3.5 rangeSet, RangeSetType
    def __init__(self, attrs, data):
        super(GMLRangeSet, self).__init__(attrs)
        self.data = data

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLRangeSet, cls).init_kwargs_from_xml(element)

        data = GMLDataBlock.from_xml(element.find('gml:DataBlock', namespaces=namespaces))
        parameters = element.find('gml:rangeParameters', namespaces=namespaces)
        if parameters is not None:
            raise NotImplementedError('Range parameters not yet implemented in gml:RangeSet.')

        kwargs.update({'data': data})
        return kwargs


class GMLDataBlock(GMLAbstractGML):
    # See 19.3.6 DataBlock
    def __init__(self, attrs, values):
        super(GMLDataBlock, self).__init__(attrs)
        self.values = values

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(GMLDataBlock, cls).init_kwargs_from_xml(element)

        components = element.find('gml:tupleList', namespaces=namespaces).text.split(',')
        values = [component.split() for component in components]

        kwargs.update({'values': values})
        return kwargs


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

    print data_mask.grid_coverage.bounded_by

    print data_mask.axes.keys()
    print data_mask.axes

#    print ds.np_arrays()
