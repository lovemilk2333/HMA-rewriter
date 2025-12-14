import sys
from pathlib import Path
from typing import List, Optional

import orjson
import typer
from rich import print
from rich.console import Console
from rich.prompt import Confirm

FILE_ENCODING = "UTF-8"
IGNORE_COMMENT = "//"

_EMPTY_DICT = {}

app = typer.Typer(
    help="HMA Config auto writer", add_completion=False, pretty_exceptions_enable=False
)

err_console = Console(stderr=True)


def _looks_like_filepath(text: str):
    text = text.strip().replace("\\", "/")
    if text.startswith("/") or (len(text) >= 2 and text[1] == ":"):
        return True

    if text.startswith("./") or text.startswith("../"):
        return True

    return False


@app.command()
def main(
    config: Path = typer.Option(
        ...,
        "-c",
        "--config",
        metavar="CONFIG_FILE",
        help="Config file path.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    output: str = typer.Option(
        ...,
        "-o",
        "--output",
        metavar="OUTPUT_FILE",
        help="Output file path. `-` for stderr, `~` to overwrite config file.",
    ),
    force_overwrite: bool = typer.Option(
        False,
        "-w",
        "--force-overwrite",
        help="Overwrite output file even if it exists.",
    ),
    mkdir: bool = typer.Option(
        False,
        "-m",
        "--mkdir",
        help="Make parent directories of output if it is a file.",
    ),
    name: str = typer.Option(
        "cnapps",
        "-n",
        "--name",
        metavar="WHITELIST_NAME",
        help="The name of the whitelist to apply.",
    ),
    ignore: List[str] = typer.Option(
        [],
        "-i",
        "--ignore",
        metavar="RULE",
        help="Ignore apps to skip applying the template. If RULE starts with `#`, it means ignore all apps of this app list. If RULE is a filepath, it loads all ignore rules from the file.",
    ),
    merge: bool = typer.Option(
        False,
        "--merge",
        help="If enabled and an app's original config exists in whitelist mode, the script will only merge whitelist names and keep other options.",
    ),
    extra_name: List[str] = typer.Option(
        [],
        "-e",
        "--extra-name",
        metavar="WHITELIST_NAME",
        help="Add other whitelists for apps.",
    ),
    force_presets: Optional[List[str]] = typer.Option(
        None,
        "-p",
        "--force-presets",
        metavar="PRESETS",
        help="Overwrite presets with specified presets.",
    ),
    force_settings_presets: Optional[List[str]] = typer.Option(
        None,
        "-s",
        "--force-settings-presets",
        metavar="SETTINGS_PRESETS",
        help="Overwrite settings presets with specified presets.",
    ),
    merge_presets: bool = typer.Option(
        False,
        "--merge-presets",
        help="Merge presets when `--force-presets` is enabled instead of overwriting.",
    ),
    merge_settings_presets: bool = typer.Option(
        False,
        "--merge-settings-presets",
        help="Merge settings presets when `--force-settings-presets` is enabled instead of overwriting.",
    ),
):
    """
    HMA Config auto writer.
    """
    assert name, "whitelist name cannot be empty"
    cnapp_whitelist_name = name
    cnapp_settings_template = {
        "useWhitelist": True,
        "excludeSystemApps": True,
        "hideInstallationSource": False,
        "hideSystemInstallationSource": False,
        "excludeTargetInstallationSource": False,
        "invertActivityLaunchProtection": False,
        "applyTemplates": [cnapp_whitelist_name],
        "applyPresets": [],
        "applySettingsPresets": ["accessibility", "dev_options", "input_method"],
        "extraAppList": [],
    }

    output_path = None
    if output == "-":
        pass
    elif output == "~":
        output_path = config
    else:
        output_path = Path(output)
        if output_path.is_file() and not force_overwrite:
            if not Confirm.ask(
                "[blue]Output file exists, do you want to overwrite?",
                default=True,
                show_default=True,
            ):
                raise typer.Abort()

        if not output_path.parent.is_dir():
            if not mkdir:
                err_console.print(
                    f"[red]Error[/red]: No such directory: `{output_path.parent}`"
                )
                raise typer.Abort()
            output_path.parent.mkdir(parents=True, exist_ok=True)

    config_json = orjson.loads(config.read_bytes())

    templates = config_json["templates"]
    assert templates.get(cnapp_whitelist_name, _EMPTY_DICT).get("isWhitelist", False), (
        f"No such whitelist `{cnapp_whitelist_name}`"
    )

    not_found_whitelists = tuple(
        filter(
            lambda n: not templates.get(n, _EMPTY_DICT).get("isWhitelist", False),
            extra_name,
        )
    )
    if not_found_whitelists:
        s = "s" if len(not_found_whitelists) > 1 else ""
        err_console.print(
            f"[red]Error[/red]: No such whitelist {s} for apps: {', '.join(not_found_whitelists)}"
        )
        raise typer.Abort()

    all_whitelists_set = set(cnapp_settings_template["applyTemplates"] + extra_name)
    cnapp_settings_template["applyTemplates"] = list(all_whitelists_set)

    def parse_ignores(
        ignores_to_parse: set[str],
    ) -> tuple[set[str], set[str]]:
        parsed: set[str] = set()
        app_lists: set[str] = set()

        for item in ignores_to_parse:
            item = item.strip()
            if item.startswith(IGNORE_COMMENT):
                continue

            item = item.split(IGNORE_COMMENT, 1)[0].strip()

            if _looks_like_filepath(item):
                with Path(item).open("r", encoding=FILE_ENCODING) as fp:
                    _parsed, _app_list = parse_ignores(set(fp.readlines()))
                    parsed |= _parsed
                    app_lists |= _app_list
            elif item.startswith("#"):
                app_list_name = item[1:]
                assert app_list_name in templates, (
                    f"No such app list for ignore rules `{app_list_name}`"
                )
                app_lists.add(app_list_name)
            else:
                parsed.add(item)

        return parsed, app_lists

    def overwrite_presets_logic(appconfig: dict | None):
        if appconfig is None or force_presets is None:
            return

        presets = (
            force_presets
            if force_presets is not None
            else cnapp_settings_template["applyPresets"]
        )

        if merge_presets:
            appconfig["applyPresets"] = list(
                set(appconfig.get("applyPresets", []) + presets)
            )
        else:
            appconfig["applyPresets"] = presets

    def overwrite_settings_presets_logic(appconfig: dict | None):
        if appconfig is None or force_settings_presets is None:
            return

        settings_presets = (
            force_settings_presets
            if force_settings_presets is not None
            else cnapp_settings_template["applySettingsPresets"]
        )

        if merge_settings_presets:
            appconfig["applySettingsPresets"] = list(
                set(appconfig.get("applySettingsPresets", []) + settings_presets)
            )
        else:
            appconfig["applySettingsPresets"] = settings_presets

    ignored_apps, ignored_lists = parse_ignores(set(ignore))
    for _app_list_name in ignored_lists:
        ignored_apps |= set(templates[_app_list_name]["appList"])

    cnapp_list = filter(
        lambda appid: appid not in ignored_apps,
        templates[cnapp_whitelist_name]["appList"],
    )

    unapplied_apps = None
    if merge:
        unapplied_apps = set()

        for appid in cnapp_list:
            appconfig = config_json["scope"].get(appid)
            overwrite_presets_logic(appconfig)
            overwrite_settings_presets_logic(appconfig)
            if appconfig is None or not appconfig.get("useWhitelist"):
                err_console.print(
                    f"[yellow]Warn[/yellow] Keep original config for app `{appid}`: `--merge` is only available for apps in whitelist mode."
                )
                unapplied_apps.add(appid)
                continue

            app_templates = appconfig.get("applyTemplates", [])
            appconfig["applyTemplates"] = list(set(app_templates) | all_whitelists_set)
    else:
        # update TEMPLATE to apply for all apps
        overwrite_presets_logic(cnapp_settings_template)
        overwrite_settings_presets_logic(cnapp_settings_template)

        for appid in cnapp_list:
            config_json["scope"][appid] = cnapp_settings_template

    if output == "-":
        sys.stderr.buffer.write(orjson.dumps(config_json))
    elif output_path:
        with output_path.open("wb") as output_file:
            output_file.write(orjson.dumps(config_json))

        if unapplied_apps:
            if len(unapplied_apps) == 1:
                print("The config of this app was unchanged:\n")
            else:
                print("The config of these apps was unchanged:\n")
            print("\n".join(unapplied_apps), end="\n\n")
        else:
            print("[green bold]OK!")
        print("[blue]>>>", output_path.resolve())


if __name__ == "__main__":
    app()
