"""Portable sticker definitions and registry; Python standard library only."""
from .core import Registry, digest, instance, resolve, validate
from .placement import attachment_matrix, placement_2d
from .interfaces import (InterfaceCatalog, assembly_target, interface_profile,
                         match_interfaces, mate_frame, validate_profile,
                         validate_profile_library)
from .connections import (compile_connection_plan, save_connection_plan,
                          solve_connection_plan, validate_connection_plan)
from .closures import (save_closed_connection_plan, validate_closure_set,
                       verify_loop_closures)
from .occupancy import (compile_occupancy_plan, occupancy_profile, occupancy_slots,
                        save_occupancy_plan, solve_occupancy_plan,
                        validate_occupancy_library, validate_occupancy_plan,
                        validate_occupancy_profile)

__all__ = ['Registry', 'digest', 'instance', 'resolve', 'validate',
           'attachment_matrix', 'placement_2d', 'InterfaceCatalog',
           'assembly_target', 'interface_profile', 'match_interfaces', 'mate_frame',
           'validate_profile', 'validate_profile_library',
           'compile_connection_plan', 'save_connection_plan',
           'solve_connection_plan', 'validate_connection_plan',
           'save_closed_connection_plan', 'validate_closure_set',
           'verify_loop_closures', 'compile_occupancy_plan', 'occupancy_profile',
           'occupancy_slots', 'save_occupancy_plan', 'solve_occupancy_plan',
           'validate_occupancy_library', 'validate_occupancy_plan',
           'validate_occupancy_profile']
