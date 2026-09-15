"""Portable sticker definitions and registry; Python standard library only."""
from .core import Registry, digest, instance, resolve, validate
from .placement import attachment_matrix, placement_2d
from .interfaces import (assembly_target, interface_profile, match_interfaces,
                         mate_frame, validate_profile, validate_profile_library)

__all__ = ['Registry', 'digest', 'instance', 'resolve', 'validate',
           'attachment_matrix', 'placement_2d', 'assembly_target',
           'interface_profile', 'match_interfaces', 'mate_frame',
           'validate_profile', 'validate_profile_library']
