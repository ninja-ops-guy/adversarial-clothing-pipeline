"""RAC-E (PHY lane): physical-transfer stack.

Printability loss, versioned production profiles, physical-transfer record
tooling, and deformation tiers T0-T3. Synthetic-only at this barrier; no
measured physical data is fabricated anywhere in this package.
"""

from . import deformation_tiers, printability, production_profiles, transfer_record

__all__ = [
    "deformation_tiers",
    "printability",
    "production_profiles",
    "transfer_record",
]
