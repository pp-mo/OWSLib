import gmlcov
import gml


namespaces = {'metOcean': 'http://def.wmo.int/metce/2013/metocean'}


class ExtensionProperty(gmlcov.ExtensionProperty):
    TAGS = ['metOcean:extensionProperty']
    EXTRA_NAMESPACES = namespaces

    @classmethod
    def from_xml(cls, element):
        return CoverageMetadata.from_xml(element[0])


class CoverageMetadata(object):
    TAGS = ['metOcean:MetOceanCoverageMetadata']
    def __init__(self, fields, masks):
        self.fields = fields
        self.masks = masks
        self._coverage_description = None


    @property
    def coverage_description(self):
        """
        The :class:`WCS.CoverageDescription` instance from which
        this :class:`CoverageMetadata` instance originates.
        Normally set by the WCS.DescribeCoverage.__init__. May be None.

        """
        return self._coverage_description

    @coverage_description.setter
    def coverage_description(self, cov_description):
        self._coverage_description = cov_description

        # Percolate the coverage description object down to the masks. 
        for mask in self.masks.values():
            mask._coverage_description = cov_description

    @classmethod
    def from_xml(cls, element):
        reference = element.find('metOcean:dataMaskReferenceProperty', namespaces=namespaces)
        fields = {field.get('fieldName'): field.text.strip()
                  for field in reference[0]}

        dm = element.find('metOcean:dataMaskProperty', namespaces=namespaces)
        masks = DataMaskProperty.from_xml(dm)

        fields = {field: masks[mask_id] for field, mask_id in fields.items()}

        # TODO: sourceObservationProperty

        return cls(fields, masks)

    def __repr__(self):
        return '<CoverageMetadata ({} fields)>'.format(len(self.fields))


@gml.non_instantiable
class DataMaskProperty(object):
    """A container of a DataMaskMemberList."""
    @classmethod
    def from_xml(cls, element):
        # Should only contain a single DataMaskMemberList
        masks = {}
        for mask in element[0]:
            mask_obj = MetOceanDataMask.from_xml(mask)
            masks[mask_obj.mask_id] = mask_obj
        return masks


class MetOceanDataMask(object):
    # XXX Should this be a subclass of GMLElement? Or ReferenceableGridCoverage?
    def __init__(self, mask_id, grid_coverage):
        self.mask_id = mask_id
        self.grid_coverage = grid_coverage
        #: The original coverage description object from whence this data
        #: mask came. This is automatically attached when a CoverageMetadata
        #: receives this mask.
        self._coverage_description = None

    @property
    def axes(self):
        """
        A dictionary showing the mapping of axes name to ...?

        """
        import numpy as np
        axes = {}

        bounding_envelope = self.grid_coverage.bounded_by
        bounding_dims = int(bounding_envelope.attrs['srsDimension'])
        labels = bounding_envelope.attrs['axisLabels'].split(' ')
        add_dims = [np.newaxis]*bounding_dims + [Ellipsis]

        domain_coords = self.grid_coverage.domain_set.np_arrays()

        try:
            extra_dims = domain_coords.values()[0].ndim
        except IndexError:
            # No domain coords to work with.
            extra_dims = 0

        if self._coverage_description is None:
            raise ValueError('Expecting to find a coverage description object. It is fundamental '
                             'to figuring out the shape of the data! (Urgh).')

        shape = self._coverage_description.domain_set.limits.highs

        axes_info = zip(labels, bounding_envelope.lows, bounding_envelope.highs, shape)
        for dim, (label, low, high, size) in enumerate(axes_info):
            arr = np.linspace(low, high, size, endpoint=True)
            new_shape = [1] * (bounding_dims + extra_dims)
            new_shape[dim] = -1
            axes[label] = Axis(label, None, None, arr.reshape(new_shape))

        for ax, arr in domain_coords.items():
            axes[ax] = Axis(ax, None, None, arr[add_dims])


        return axes

    @classmethod
    def from_xml(cls, element):
        datamask_id = element.get(gml.apply_namespace('gml:id', gml.namespaces))
        actual_mask = gmlcov.ReferenceableGridCoverage.from_xml(element[0])
        return cls(datamask_id, actual_mask)


class Axis(object):
    """
    Represents an axis of the coverage. There is no such concept in the specification,
    this is purely for simplicity of user interface.

    An Axis instance stores information about CRS, axis label, units of measure,
    ordinate values (numpy arrays). An Axis instance can be indexed (square brackets) to
    produce a :class:`Trim` object suitable for passing to the subset kwarg of getCoverage.

    """
    def __init__(self, label, units, crs, ordinates):
        self.label, self.units, self.crs, self.ordinates = label, units, crs, ordinates

    def __getitem__(self, keys):
        return Trim(self, keys)


class Trim(object):
    def __init__(self, axis, index_slice):
        self.axis = axis
        self.index_slice = index_slice

