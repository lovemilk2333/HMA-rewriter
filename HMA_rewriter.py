import sys
import argparse
from pathlib import Path
from json import load, dump, dumps

parser = argparse.ArgumentParser(description='HMA Config auto writer')
parser.add_argument('-c', '--config', type=Path, metavar='CONFIG_FILE',
                    required=True, help='config file path')
parser.add_argument('-o', '--output', type=str, required=True, metavar='OUTPUT_FILE',
                    help='output file path, `-` means stdout, `~` to overwrite config file')
parser.add_argument('-w', '--force-overwrite', action='store_false',
                    help='overwrite output file even the file exists')
parser.add_argument('-m', '--mkdir', action='store_false',
                    help='make parent dirs of output if output is a file')
parser.add_argument('-n', '--name', type=str, default='cnapps', metavar='WHITELIST_NAME',
                    help='the name of whitelist you want to use as apply')
parser.add_argument('-i', '--ignore', default=[], metavar='APPID', action='append',
                    help='ignore apps skip to apply template (allow access these apps only)')
parser.add_argument('--merge', action='store_true',
                    help='if enabled and the app\'s original config exists in whitelist mode, the script will only merge whitelist names and keep other options')

args = parser.parse_args()

assert args.name, 'whitelist name cannot be empty'
CNAPP_WHITELIST_NAME = args.name
FILE_ENCODING = 'u8'
CNAPP_SETTINGS_TEMPLATE = {
    "useWhitelist": True,
    "excludeSystemApps": True,
    "hideInstallationSource": False,
    "hideSystemInstallationSource": False,
    "excludeTargetInstallationSource": False,
    "invertActivityLaunchProtection": False,
    "applyTemplates": [
        CNAPP_WHITELIST_NAME
    ],
    "applyPresets": [],
    "applySettingsPresets": [],
    "extraAppList": []
}

output = args.output
if output != '-':
    output = args.config if output == '~' else Path(output)
    if output.is_file() and not args.force_overwrite:
        print('output file exists, aborted.\nuse `-w` or `--force-overwrite` to ignore aborting')
        sys.exit(-1)

    if args.mkdir and not output.parent.is_dir():
        output.mkdir(parents=True)


with args.config.open('r', encoding=FILE_ENCODING) as config_fp:
    config_json = load(config_fp)

templates = config_json['templates']
assert CNAPP_WHITELIST_NAME in templates, f'no such whitelist `{CNAPP_WHITELIST_NAME}`'
CNAPP_LIST = filter(lambda appid: appid not in args.ignore,
                    templates[CNAPP_WHITELIST_NAME]['appList'])

use_merge = args.merge
for appid in CNAPP_LIST:
    if not use_merge:
        config_json['scope'][appid] = CNAPP_SETTINGS_TEMPLATE
        continue

    appconfig = config_json['scope'].get(appid)
    if appconfig is None:
        config_json['scope'][appid] = CNAPP_SETTINGS_TEMPLATE
        continue

    is_whitelist = appconfig['useWhitelist']
    if not is_whitelist:
        config_json['scope'][appid] = CNAPP_SETTINGS_TEMPLATE
        continue

    app_templates = appconfig['applyTemplates']
    if CNAPP_WHITELIST_NAME not in app_templates:
        app_templates.append(CNAPP_SETTINGS_TEMPLATE)

if output == '-':
    print(dumps(config_json))
else:
    with output.open('w', encoding=FILE_ENCODING) as output_file:
        dump(config_json, output_file)

    print('OK')
