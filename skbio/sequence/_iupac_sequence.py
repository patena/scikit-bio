# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from __future__ import absolute_import, division, print_function
from future.utils import with_metaclass

from abc import ABCMeta, abstractproperty
from itertools import product

import numpy as np
from six import string_types

from skbio.util._decorator import classproperty, overrides
from skbio.util._misc import MiniRegistry
from ._sequence import Sequence


class IUPACSequence(with_metaclass(ABCMeta, Sequence)):
    """Store biological sequence data conforming to the IUPAC character set.

    This is an abstract base class (ABC) that cannot be instantiated.

    Attributes
    ----------
    values
    metadata
    positional_metadata
    alphabet
    gap_chars
    nondegenerate_chars
    degenerate_chars
    degenerate_map

    Raises
    ------
    ValueError
        If sequence characters are not in the IUPAC character set [1]_.

    See Also
    --------
    DNA
    RNA
    Protein

    References
    ----------
    .. [1] Nomenclature for incompletely specified bases in nucleic acid
       sequences: recommendations 1984.
       Nucleic Acids Res. May 10, 1985; 13(9): 3021-3030.
       A Cornish-Bowden

    """
    # ASCII is built such that the difference between uppercase and lowercase
    # is the 6th bit.
    _ascii_invert_case_bit_offset = 32
    _number_of_extended_ascii_codes = 256
    _ascii_lowercase_boundary = 90
    __validation_mask = None
    __degenerate_codes = None
    __nondegenerate_codes = None
    __gap_codes = None

    @classproperty
    def _validation_mask(cls):
        # TODO These masks could be defined (as literals) on each concrete
        # object. For now, memoize!
        if cls.__validation_mask is None:
            cls.__validation_mask = np.invert(np.bincount(
                np.fromstring(''.join(cls.alphabet), dtype=np.uint8),
                minlength=cls._number_of_extended_ascii_codes).astype(bool))
        return cls.__validation_mask

    @classproperty
    def _degenerate_codes(cls):
        if cls.__degenerate_codes is None:
            degens = cls.degenerate_chars
            cls.__degenerate_codes = np.asarray([ord(d) for d in degens])
        return cls.__degenerate_codes

    @classproperty
    def _nondegenerate_codes(cls):
        if cls.__nondegenerate_codes is None:
            nondegens = cls.nondegenerate_chars
            cls.__nondegenerate_codes = np.asarray([ord(d) for d in nondegens])
        return cls.__nondegenerate_codes

    @classproperty
    def _gap_codes(cls):
        if cls.__gap_codes is None:
            gaps = cls.gap_chars
            cls.__gap_codes = np.asarray([ord(g) for g in gaps])
        return cls.__gap_codes

    @classproperty
    def alphabet(cls):
        """Return valid IUPAC characters.

        This includes gap, non-degenerate, and degenerate characters.

        Returns
        -------
        set
            Valid IUPAC characters.

        """
        return cls.degenerate_chars | cls.nondegenerate_chars | cls.gap_chars

    @classproperty
    def gap_chars(cls):
        """Return characters defined as gaps.

        Returns
        -------
        set
            Characters defined as gaps.

        """
        return set('-.')

    @classproperty
    def degenerate_chars(cls):
        """Return degenerate IUPAC characters.

        Returns
        -------
        set
            Degenerate IUPAC characters.

        """
        return set(cls.degenerate_map)

    @abstractproperty
    @classproperty
    def nondegenerate_chars(cls):
        """Return non-degenerate IUPAC characters.

        Returns
        -------
        set
            Non-degenerate IUPAC characters.

        """
        return set()  # pragma: no cover

    @abstractproperty
    @classproperty
    def degenerate_map(cls):
        """Return mapping of degenerate to non-degenerate characters.

        Returns
        -------
        dict (set)
            Mapping of each degenerate IUPAC character to the set of
            non-degenerate IUPAC characters it represents.

        """
        return set()  # pragma: no cover

    @property
    def _motifs(self):
            return _motifs

    @overrides(Sequence)
    def __init__(self, sequence, metadata=None, positional_metadata=None,
                 validate=True, lowercase=False):
        super(IUPACSequence, self).__init__(
            sequence, metadata, positional_metadata)

        if lowercase is False:
            pass
        elif lowercase is True or isinstance(lowercase, string_types):
            lowercase_mask = self._bytes > self._ascii_lowercase_boundary
            self._convert_to_uppercase(lowercase_mask)

            # If it isn't True, it must be a string_type
            if not (lowercase is True):
                self.positional_metadata[lowercase] = lowercase_mask
        else:
            raise TypeError("lowercase keyword argument expected a bool or "
                            "string, but got %s" % type(lowercase))

        if validate:
            self._validate()

    def _convert_to_uppercase(self, lowercase):
        if np.any(lowercase):
            with self._byte_ownership():
                self._bytes[lowercase] ^= self._ascii_invert_case_bit_offset

    def _validate(self):
        # This is the fastest way that we have found to identify the
        # presence or absence of certain characters (numbers).
        # It works by multiplying a mask where the numbers which are
        # permitted have a zero at their index, and all others have a one.
        # The result is a vector which will propogate counts of invalid
        # numbers and remove counts of valid numbers, so that we need only
        # see if the array is empty to determine validity.
        invalid_characters = np.bincount(
            self._bytes, minlength=self._number_of_extended_ascii_codes
        ) * self._validation_mask
        if np.any(invalid_characters):
            bad = list(np.where(
                invalid_characters > 0)[0].astype(np.uint8).view('|S1'))
            raise ValueError(
                "Invalid character%s in sequence: %r. Valid IUPAC characters: "
                "%r" % ('s' if len(bad) > 1 else '',
                        [str(b.tostring().decode("ascii")) for b in bad] if
                        len(bad) > 1 else bad[0],
                        list(self.alphabet)))

    def lowercase(self, lowercase):
        """Return a case-sensitive string representation of the sequence.

        Parameters
        ----------
        lowercase: str or boolean vector
            If lowercase is a boolean vector, it is used to set sequence
            characters to lowercase in the output string. True values in the
            boolean vector correspond to lowercase characters. If lowercase
            is a str, it is treated like a key into the positional metadata,
            pointing to a column which must be a boolean vector.
            That boolean vector is then used as described previously.

        Returns
        -------
        str
            String representation of sequence with specified characters set to
            lowercase.

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('ACGT')
        >>> s.lowercase([True, True, False, False])
        'acGT'
        >>> s = DNA('ACGT',
        ...         positional_metadata={'exons': [True, False, False, True]})
        >>> s.lowercase('exons')
        'aCGt'

        Constructor automatically populates a column in positional metadata
        when the ``lowercase`` keyword argument is provided with a column name:

        >>> s = DNA('ACgt', lowercase='introns')
        >>> s.lowercase('introns')
        'ACgt'
        >>> s = DNA('ACGT', lowercase='introns')
        >>> s.lowercase('introns')
        'ACGT'

        """
        index = self._munge_to_index_array(lowercase)
        outbytes = self._bytes.copy()
        outbytes[index] ^= self._ascii_invert_case_bit_offset
        return str(outbytes.tostring().decode('ascii'))

    def gaps(self):
        """Find positions containing gaps in the biological sequence.

        Returns
        -------
        1D np.ndarray (bool)
            Boolean vector where ``True`` indicates a gap character is present
            at that position in the biological sequence.

        See Also
        --------
        has_gaps

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('AC-G-')
        >>> s.gaps()
        array([False, False,  True, False,  True], dtype=bool)

        """
        return np.in1d(self._bytes, self._gap_codes)

    def has_gaps(self):
        """Determine if the sequence contains one or more gap characters.

        Returns
        -------
        bool
            Indicates whether there are one or more occurrences of gap
            characters in the biological sequence.

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('ACACGACGTT')
        >>> s.has_gaps()
        False
        >>> t = DNA('A.CAC--GACGTT')
        >>> t.has_gaps()
        True

        """
        # TODO use count, there aren't that many gap chars
        # TODO: cache results
        return bool(self.gaps().any())

    def degenerates(self):
        """Find positions containing degenerate characters in the sequence.

        Returns
        -------
        1D np.ndarray (bool)
            Boolean vector where ``True`` indicates a degenerate character is
            present at that position in the biological sequence.

        See Also
        --------
        has_degenerates
        nondegenerates
        has_nondegenerates

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('ACWGN')
        >>> s.degenerates()
        array([False, False,  True, False,  True], dtype=bool)

        """
        return np.in1d(self._bytes, self._degenerate_codes)

    def has_degenerates(self):
        """Determine if sequence contains one or more degenerate characters.

        Returns
        -------
        bool
            Indicates whether there are one or more occurrences of degenerate
            characters in the biological sequence.

        See Also
        --------
        degenerates
        nondegenerates
        has_nondegenerates

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('ACAC-GACGTT')
        >>> s.has_degenerates()
        False
        >>> t = DNA('ANCACWWGACGTT')
        >>> t.has_degenerates()
        True

        """
        # TODO use bincount!
        # TODO: cache results
        return bool(self.degenerates().any())

    def nondegenerates(self):
        """Find positions containing non-degenerate characters in the sequence.

        Returns
        -------
        1D np.ndarray (bool)
            Boolean vector where ``True`` indicates a non-degenerate character
            is present at that position in the biological sequence.

        See Also
        --------
        has_nondegenerates
        degenerates
        has_nondegenerates

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('ACWGN')
        >>> s.nondegenerates()
        array([ True,  True, False,  True, False], dtype=bool)

        """
        return np.in1d(self._bytes, self._nondegenerate_codes)

    def has_nondegenerates(self):
        """Determine if sequence contains one or more non-degenerate characters

        Returns
        -------
        bool
            Indicates whether there are one or more occurrences of
            non-degenerate characters in the biological sequence.

        See Also
        --------
        nondegenerates
        degenerates
        has_degenerates

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('NWNNNNNN')
        >>> s.has_nondegenerates()
        False
        >>> t = DNA('ANCACWWGACGTT')
        >>> t.has_nondegenerates()
        True

        """
        # TODO: cache results
        return bool(self.nondegenerates().any())

    def degap(self):
        """Return a new sequence with gap characters removed.

        Returns
        -------
        IUPACSequence
            A new sequence with all gap characters removed.

        See Also
        --------
        gap_chars

        Notes
        -----
        The type and metadata of the result will be the same as the
        biological sequence. If positional metadata is present, it will be
        filtered in the same manner as the sequence characters and included in
        the resulting degapped sequence.

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('GGTC-C--ATT-C.',
        ...         positional_metadata={'quality':range(14)})
        >>> s.degap()
        DNA
        -----------------------------
        Positional metadata:
            'quality': <dtype: int64>
        Stats:
            length: 9
            has gaps: False
            has degenerates: False
            has non-degenerates: True
            GC-content: 55.56%
        -----------------------------
        0 GGTCCATTC

        """
        return self[np.invert(self.gaps())]

    def expand_degenerates(self):
        """Yield all possible non-degenerate versions of the sequence.

        Yields
        ------
        IUPACSequence
            Non-degenerate version of the sequence.

        See Also
        --------
        degenerate_map

        Notes
        -----
        There is no guaranteed ordering to the non-degenerate sequences that
        are yielded.

        Each non-degenerate sequence will have the same type, metadata,
        and positional metadata as the biological sequence.

        Examples
        --------
        >>> from skbio import DNA
        >>> seq = DNA('TRG')
        >>> seq_generator = seq.expand_degenerates()
        >>> for s in sorted(seq_generator, key=str):
        ...     s
        ...     print('')
        DNA
        -----------------------------
        Stats:
            length: 3
            has gaps: False
            has degenerates: False
            has non-degenerates: True
            GC-content: 33.33%
        -----------------------------
        0 TAG
        <BLANKLINE>
        DNA
        -----------------------------
        Stats:
            length: 3
            has gaps: False
            has degenerates: False
            has non-degenerates: True
            GC-content: 66.67%
        -----------------------------
        0 TGG
        <BLANKLINE>

        """
        degen_chars = self.degenerate_map
        nonexpansion_chars = self.nondegenerate_chars.union(self.gap_chars)

        expansions = []
        for char in self:
            char = str(char)
            if char in nonexpansion_chars:
                expansions.append(char)
            else:
                expansions.append(degen_chars[char])

        result = product(*expansions)
        return (self._to(sequence=''.join(nondegen_seq)) for nondegen_seq in
                result)

    def find_motifs(self, motif_type, min_length=1, ignore=None):
        """Search the biological sequence for motifs.

        Options for `motif_type`:

        Parameters
        ----------
        motif_type : str
            Type of motif to find.
        min_length : int, optional
            Only motifs at least as long as `min_length` will be returned.
        ignore : 1D array_like (bool), optional
            Boolean vector indicating positions to ignore when matching.

        Yields
        ------
        slice
            Location of the motif in the biological sequence.

        Raises
        ------
        ValueError
            If an unknown `motif_type` is specified.

        Examples
        --------
        >>> from skbio import DNA
        >>> s = DNA('ACGGGGAGGCGGAG')
        >>> for motif_slice in s.find_motifs('purine-run', min_length=2):
        ...     motif_slice
        ...     str(s[motif_slice])
        slice(2, 9, None)
        'GGGGAGG'
        slice(10, 14, None)
        'GGAG'

        Gap characters can disrupt motifs:

        >>> s = DNA('GG-GG')
        >>> for motif_slice in s.find_motifs('purine-run'):
        ...     motif_slice
        slice(0, 2, None)
        slice(3, 5, None)

        Gaps can be ignored by passing the gap boolean vector to `ignore`:

        >>> s = DNA('GG-GG')
        >>> for motif_slice in s.find_motifs('purine-run', ignore=s.gaps()):
        ...     motif_slice
        slice(0, 5, None)

        """
        if motif_type not in self._motifs:
            raise ValueError("Not a known motif (%r) for this sequence (%s)." %
                             (motif_type, self.__class__.__name__))

        return self._motifs[motif_type](self, min_length, ignore)

    @overrides(Sequence)
    def _constructor(self, **kwargs):
        return self.__class__(validate=False, lowercase=False, **kwargs)

    @overrides(Sequence)
    def _repr_stats(self):
        """Define custom statistics to display in the sequence's repr."""
        stats = super(IUPACSequence, self)._repr_stats()
        stats.append(('has gaps', '%r' % self.has_gaps()))
        stats.append(('has degenerates', '%r' % self.has_degenerates()))
        stats.append(('has non-degenerates', '%r' % self.has_nondegenerates()))
        return stats


_motifs = MiniRegistry()

# Leave this at the bottom
_motifs.interpolate(IUPACSequence, "find_motifs")
