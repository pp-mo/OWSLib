import gml

namespaces = {'gmlcov': 'http://www.opengis.net/gmlcov/1.0'}


class ReferenceableGridCoverage(gml.GMLAbstractGML):
    # See 6.6.9 ReferenceableGridCoverage
    def __init__(self, attrs, domain_set, range_type, range_set, bounded_by):
        super(ReferenceableGridCoverage, self).__init__(attrs)
        self.domain_set, self.range_type, self.range_set = domain_set, range_type, range_set
        # NOTE: I didn't see this in the spec...
        self.bounded_by = bounded_by

    @classmethod
    def init_kwargs_from_xml(cls, element):
        kwargs = super(ReferenceableGridCoverage, cls).init_kwargs_from_xml(element)

        range_set = gml.GMLRangeSet.from_xml(element.find('gml:rangeSet',
                                                          namespaces=gml.namespaces))

        domain_set = gml.GMLReferenceableGridByArray.from_xml(element.find('gml:domainSet',
                                                                           namespaces=gml.namespaces)[0])

        bounded_by = gml.GMLEnvelope.from_xml(element.find('gml:boundedBy', gml.namespaces)[0])
        # Not implemented: rangeType, boundedBy

        kwargs.update({'domain_set': domain_set, 'range_type': None, 'range_set': range_set, 'bounded_by': bounded_by})
        return kwargs

    def __repr__(self):
        return 'ReferenceableGridCoverage({!r}, {}, {}, {}, {})'.format(self.attrs, self.domain_set, self.range_type, self.range_set, self.bounded_by)


class ExtensionTypeTracking(type):
    """A metaclass to keep track of any extension subclasses."""
    def __init__(cls, name, bases, dct):
        # Update the _subclasses dictionary for any subclass which
        # is created.
        if isinstance(cls.TAGS, basestring):
            raise TypeError("The TAGS class attribute shouldn't be a string - it should be an iterable of strings.")
        for tag in cls.TAGS or []:
            cls._subclasses[tag] = cls

        super(ExtensionTypeTracking, cls).__init__(name, bases, dct)


class Extension(gml.GMLAbstractGML):
    # Seems undocumented. :(
    __metaclass__ = ExtensionTypeTracking
    TAGS = ['gmlcov:Extension']
    _subclasses = {}

    @classmethod
    def subclass_from_xml(cls, element):
        subcls = cls._subclasses[gml.de_namespace(element.tag, namespaces)]
        return subcls.from_xml(element)

    @classmethod
    def find(cls, parent_element, allow_none=True):
        """Find a single XML element which can be used by this GML concept."""
        ns = gml.namespaces.copy()

        element = None
        for tag in cls.TAGS or []:
            element = parent_element.find(tag, namespaces=ns)
            if element is not None:
                break
        if element is None and not allow_none:
            raise ValueError('Tags {} not found.'.format(', '.join(cls.TAGS or [])))
        return element

    @classmethod
    def from_xml(cls, element):
        return ExtensionProperty.subclass_from_xml(element[0])


class ExtensionProperty(gml.GMLAbstractGML):
    # Seems undocumented. :(
    __metaclass__ = ExtensionTypeTracking
    _subclasses = {}

    @classmethod
    def subclass_from_xml(cls, element):
        ns = namespaces.copy()
        for subclass in cls._subclasses.values():
            ns.update(getattr(subclass, 'EXTRA_NAMESPACES', {}))
        subcls = cls._subclasses[gml.de_namespace(element.tag, ns)]
        return subcls.from_xml(element)

    @classmethod
    def find(cls, parent_element, allow_none=True):
        """Find a single XML element which can be used by this GML concept."""
        ns = gml.namespaces.copy()
        ns.update(getattr(cls, 'EXTRA_NAMESPACES', {}))

        element = None
        for tag in cls.TAGS or []:
            element = parent_element.find(tag, namespaces=ns)
            if element is not None:
                break
        if element is None and not allow_none:
            raise ValueError('Tags {} not found.'.format(', '.join(cls.TAGS or [])))
        return element


if __name__ == '__main__':
    pass