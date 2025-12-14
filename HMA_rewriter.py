import sys
import argparse
from pathlib import Path
from json import load, dump, dumps

FILE_ENCODING = 'UTF-8'
IGNORE_COMMENT = '//'

_EMPTY_DICT = {}


def confirm_box(prompt: str = "", empty_as_true: bool = False):
    if 'Y/n' not in prompt:
        prompt = f'{prompt} [Y/n] '

    try:
        ipt = input(prompt)
        if len(ipt) == 0 and empty_as_true:
            return True

        return ipt.lower() == 'y'
    except KeyboardInterrupt:
        return False


parser = argparse.ArgumentParser(description='HMA Config auto writer')
parser.add_argument('-c', '--config', type=Path, metavar='CONFIG_FILE',
                    required=True, help='config file path')
parser.add_argument('-o', '--output', type=str, required=True, metavar='OUTPUT_FILE',
                    help='output file path, `-` means stderr, `~` to overwrite config file')
parser.add_argument('-w', '--force-overwrite', action='store_true',
                    help='overwrite output file even the file exists')
parser.add_argument('-m', '--mkdir', action='store_true',
                    help='make parent dirs of output if output is a file')
parser.add_argument('-n', '--name', type=str, default='cnapps', metavar='WHITELIST_NAME',
                    help='the name of whitelist you want to use as apply')
parser.add_argument('-i', '--ignore', default=[], metavar='RULE', action='append',
                    help=f'ignore apps skip to apply template (to allow other apps access these apps only)\nif RULE starts with `#`, it means ignore all apps of this app list (either blacklist or whitelist)\nif RULE is a filepath, it means load all ignore rules in this text file breaks by line (use `{FILE_ENCODING}` encoding)\nuse `//` to add comment')
parser.add_argument('--merge', action='store_true',
                    help='if enabled and the app\'s original config exists in whitelist mode, the script will only merge whitelist names and keep other options')
parser.add_argument('-e', '--extra-name', action='append', default=[],
                    metavar='WHITELIST_NAME', help='add other whitelists for apps')

args = parser.parse_args()

assert args.name, 'whitelist name cannot be empty'
CNAPP_WHITELIST_NAME = args.name
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
    "applySettingsPresets": [
        "accessibility",
        "dev_options",
        "input_method"
    ],
    "extraAppList": []
}

output = args.output
if output == '-':
    pass
elif output == '~':
    output = args.config
else:
    output = Path(output)
    if output.is_file() and not args.force_overwrite:
        # print('output file exists, aborted.\nuse `-w` or `--force-overwrite` to ignore aborting')
        if not confirm_box('output file exists, do you want to continue? (use `-w` or `--force-overwrite` to skip this interrupt)', empty_as_true=True):
            print('aborted')
            sys.exit(-1)

    if not output.parent.is_dir():
        assert args.mkdir, f'no such directory: `{output.parent}`'
        output.mkdir(parents=True)


with args.config.open('r', encoding=FILE_ENCODING) as config_fp:
    config_json = load(config_fp)

templates = config_json['templates']
assert templates.get(CNAPP_WHITELIST_NAME, _EMPTY_DICT).get(
    'isWhitelist', False), f'no such whitelist `{CNAPP_WHITELIST_NAME}`'

not_found_whitelists = tuple(
    filter(lambda name: not templates.get(name, _EMPTY_DICT).get(
        'isWhitelist', False), args.extra_name)
)
assert len(not_found_whitelists) <= 0, \
    f'no such whitelist{(len(not_found_whitelists) > 1) * "s"} for apps: `{", ".join(not_found_whitelists)}`'

CNAPP_SETTINGS_TEMPLATE['applyTemplates'] = list(
    set(CNAPP_SETTINGS_TEMPLATE['applyTemplates'] + args.extra_name)
)


def _looks_like_filepath(text: str):
    text = text.strip().replace('\\', '/')
    if text.startswith('/') or (len(text) >= 2 and text[1] == ':'):
        return True

    if text.startswith('./') or text.startswith('../'):
        return True

    return False


def parse_ignores(ignores: set[str]) -> tuple[set[str], set[str]]:
    parsed: set[str] = set()
    app_lists: set[str] = set()

    for ignore in ignores:
        ignore = ignore.strip()
        if ignore.startswith(IGNORE_COMMENT):
            continue

        ignore = ignore.split(IGNORE_COMMENT, 1)[0].strip()

        if _looks_like_filepath(ignore):
            with Path(ignore).open('r', encoding=FILE_ENCODING) as fp:
                _parsed, _app_list = parse_ignores(set(fp.readlines()))
                parsed |= _parsed
                app_lists |= _app_list
        elif ignore.startswith('#'):
            app_list_name = ignore[1:]
            assert app_list_name in templates, f'no such app list for ignore rules `{app_list_name}`'
            app_lists.add(app_list_name)
        else:
            parsed.add(ignore)

    return parsed, app_lists


ignored_apps, ignored_lists = parse_ignores(set(args.ignore))
for _app_list_name in ignored_lists:
    ignored_apps |= set(templates[_app_list_name]['appList'])

CNAPP_LIST = filter(
    lambda appid: appid not in ignored_apps,
    templates[CNAPP_WHITELIST_NAME]['appList']
)

unapplied_apps = None
if args.merge:
    unapplied_apps = set()

    for appid in CNAPP_LIST:
        appconfig = config_json['scope'].get(appid)
        if appconfig is None or not appconfig['useWhitelist']:
            # config_json['scope'][appid] = CNAPP_SETTINGS_TEMPLATE
            # continue
            print(
                f'[WARN] keep original config for app `{appid}`: `--merge` is only available for app which in whitelist mode')
            unapplied_apps.add(appid)
            continue

        app_templates = appconfig['applyTemplates']
        if CNAPP_WHITELIST_NAME not in app_templates:
            app_templates.append(CNAPP_SETTINGS_TEMPLATE)
else:
    for appid in CNAPP_LIST:
        config_json['scope'][appid] = CNAPP_SETTINGS_TEMPLATE

if output == '-':
    print(dumps(config_json), file=sys.stderr)
else:
    with output.open('w', encoding=FILE_ENCODING) as output_file:
        dump(config_json, output_file)

    if unapplied_apps:
        if len(unapplied_apps) == 1:
            print('the config of this app was not changed:', end='\n\n')
        else:
            print('the config of those apps was not changed:', end='\n\n')
        print('\n'.join(unapplied_apps), end='\n\n')
    else:
        print('OK!')
    print(output.resolve())
