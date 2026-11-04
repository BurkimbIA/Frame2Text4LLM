from beartype.claw import beartype_this_package

from .package_metadata import (
    __author__,
    __doc__,
    __email__,
    __name__,
    __url__,
    __version__,
)

beartype_this_package()
