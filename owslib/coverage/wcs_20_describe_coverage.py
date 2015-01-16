import gml
from wcs200 import WCS_names as namespaces

from gml import de_namespace, non_instantiable


class ExtensionTypeTracking(type):
    """A metaclass to keep track of any extension subclasses."""
    def __init__(cls, name, bases, dct):
        # Update the _subclasses dictionary for any subclass which
        # is created.
        for tag in cls.TAGS or []:
            cls._subclasses[tag] = cls

        super(ExtensionTypeTracking, cls).__init__(name, bases, dct)


class WCSExtension(object):
    #: The GML tags where this GML concept can be found.
    TAGS = None

    def __init__(self):
        #: The CoverageDescription object from which this extension came.
        self._coverage_description = None

    __metaclass__ = ExtensionTypeTracking
    _subclasses = {}

    @classmethod
    def subclass_from_xml(cls, element):
        ns = namespaces.copy()
        for subclass in cls._subclasses.values():
            ns.update(getattr(subclass, 'EXTRA_NAMESPACES', {}))
        subcls = cls._subclasses[de_namespace(element.tag, ns)]
        return subcls.from_xml(element)

    def __repr__(self):
        return '<{} instance>'.format(self.__class__.__name__)

    @classmethod
    def find(cls, parent_element, allow_none=True):
        """Find a single XML element which can be used by this GML concept."""
        ns = namespaces.copy()
        ns.update(getattr(cls, 'EXTRA_NAMESPACES', {}))

        element = None
        for tag in cls.TAGS or []:
            element = parent_element.find(tag, namespaces=ns)
            if element is not None:
                break
        if element is None and not allow_none:
            raise ValueError('Tags {} not found.'.format(', '.join(cls.TAGS or [])))
        return element

    @classmethod
    def find_subclass_element(cls, parent_element):
        for tag, subclass in cls._subclasses.items():
            ns = namespaces.copy()
            ns.update(getattr(subclass, 'EXTRA_NAMESPACES', {}))
            element = parent_element.find(tag, namespaces=ns)
            if element is not None:
                yield element


@non_instantiable
class GMLCOVMetadata(WCSExtension):
    """
    A WCS extension which is used in the DescribeCoverage functionality.

    See 6.3 Metadata of gmlcov spec. Specifically:
    The metaData component is a carrier for any kind of application
    dependent metadata. Hence, no requirements are imposed here.

    In practice, this tag has been used as a WCS extension found in the
    DescribeCoverage class. This item itself contains only a single tag,
    namely a GMLCOV:Extension instance.

    """
    TAGS = ['gmlcov:metadata']
    EXTRA_NAMESPACES = {'gmlcov': 'http://www.opengis.net/gmlcov/1.0'}

    @classmethod
    def from_xml(cls, element):
        import gmlcov
        return gmlcov.Extension.subclass_from_xml(element[0])


class DescribeCoverage(object):
    def __init__(self, domain_set, range_type, extension=None):
        self.domain_set = domain_set
        self.extension = extension

        # Provide sufficient context of this coverage to allow it
        # to do what it likes.
        if extension is not None:
            self.extension.coverage_description = self

    @classmethod
    def from_xml(cls, element):
        domain_set = gml.GMLdomainSet.from_xml(gml.GMLdomainSet.find_one(element))

        # Doesn't seem to be documented:
        extension_elements = list(WCSExtension.find_subclass_element(element))
        if extension_elements:
            assert len(extension_elements) == 1
            extension = WCSExtension.subclass_from_xml(extension_elements[0])
        else:
            extension = None

        return cls(domain_set, None, extension=extension)

    def __repr__(self):
        return '<DescribeCoverage instance>'


#if __name__ == '__main__':
#    import metOcean
#    WCS(URL, extensions=[metOcean])




