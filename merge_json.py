import sys
import argparse
from pathlib import Path
from json import load, dump, dumps

FILE_ENCODING = 'u8'
CNAPP_WHILTELIST_NAME = 'cnapps'
CNAPP_SETTINGS_TEMPLATE = {
    "useWhitelist": True,
    "excludeSystemApps": True,
    "hideInstallationSource": False,
    "hideSystemInstallationSource": False,
    "excludeTargetInstallationSource": False,
    "invertActivityLaunchProtection": False,
    "applyTemplates": [
        CNAPP_WHILTELIST_NAME
    ],
    "applyPresets": [],
    "applySettingsPresets": [],
    "extraAppList": []
}

parser = argparse.ArgumentParser(description='HMA Config auto writer')
parser.add_argument('-c', '--config', type=Path, required=True, help='config file path')
parser.add_argument('-o', '--output', type=str, required=True, help='output file path, `-` means stdout, `~` to overwrite config file')
parser.add_argument('-w', '--force-overwrite', action='store_false', help='overwrite output file even the file exists')
parser.add_argument('-m', '--mkdir', action='store_false', help='make parent dirs of output if output is a file')

args = parser.parse_args()

with args.config.open('r', encoding=FILE_ENCODING) as config_fp:
    config_json = load(config_fp)
    CNAPP_LIST = config_json['templates'][CNAPP_WHILTELIST_NAME]['appList']

for app_id in CNAPP_LIST:
    config_json['scope'][app_id] = CNAPP_SETTINGS_TEMPLATE

output = args.output
if output == '-':
    print(dumps(config_json))
else:
    output = args.config if output == '~' else Path(output)
    if output.is_file() and not args.force_overwrite:
        print('output file exists, aborted.\nuse `-w` or `--force-overwrite` to ignore aborting')
        sys.exit(-1)

    if args.mkdir and not output.parent.is_dir():
        output.mkdir(parents=True)

    with output.open('w', encoding=FILE_ENCODING) as output_file:
        dump(config_json, output_file)

    print('OK')
