#-----------------------------------------------------------------------------
# Copyright (c) 2018-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import os
import sys

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
    get_package_paths,
)

# The path to the package
pkg_base_path, pkg_dir = get_package_paths("torch")


# Collect all binaries and data files
# NOTE: The latest torch has A LOT of binaries and data files, so we collect everything in the package.
binaries = collect_dynamic_libs("torch")
datas = collect_data_files("torch", include_py_files=True)
hiddenimports = collect_submodules("torch")

# The following DLLs are required by the PyTorch C extension modules, but are not automatically collected because
# they are not directly linked to any of the modules. They are instead loaded at runtime via `ctypes.CDLL()`.
# See `torch/__init__.py`.
# For `torch.version.cuda`
if sys.platform == "win32":
    for lib_name in ("cudart64_110", "nvToolsExt64_1"):
        binaries.append(
            (os.path.join(pkg_dir, "lib", f"{lib_name}.dll"), "torch/lib")
        )

# Metadata for torch must be collected for distutils to work.
metadata = copy_metadata("torch")
datas += metadata
