"""Update the manifest file."""

import json
import os
import sys
import re

def update_manifest():
    """Update the manifest file."""
    version = "0.0.0"
    manifest_path = False

    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            version = str(sys.argv[index + 1]).replace("v", "")
        if value in ["--path", "-P"]:
            manifest_path = str(sys.argv[index + 1])[1:-1]

    if not manifest_path:
        sys.exit("Missing path to manifest file")

    with open(
        f"{os.getcwd()}/{manifest_path}/manifest.json",
        encoding="UTF-8",
    ) as manifestfile:
        manifest = json.load(manifestfile)

    manifest["version"] = version


    pattern = r'VERSION\s*=\s*"\d+\.\d+\.\d+"'
    replacement = f'VERSION = "{version}"'

    with open(f"{os.getcwd()}/{manifest_path}/const.py",'r') as file:
        filedata = file.read()
        filedata = re.sub(pattern, replacement, filedata, flags=re.MULTILINE)
    with open(f"{os.getcwd()}/{manifest_path}/const.py",'w') as file:
        file.write(filedata)

    with open(
        f"{os.getcwd()}/{manifest_path}/manifest.json",
        "w",
        encoding="UTF-8",
    ) as manifestfile:
        manifestfile.write(
            json.dumps(
                {
                    "domain": manifest["domain"],
                    "name": manifest["name"],
                    **{
                        k: v
                        for k, v in sorted(manifest.items())
                        if k not in ("domain", "name")
                    },
                },
                indent=4,
            )
        )


update_manifest()