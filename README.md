# HMA-rewriter

a simple Python script to rewrite HMA config JSON for me

auto patch app config for apps of template called `cnapps` as whitelist with `applyTemplates: ["cnapps"]` only

## Usage
```sh
python ./HMA_rewriter.py -c <config-file> -o <output-file>
```

example
```sh
python ./HMA_rewriter.py -c HMA_Config_1759302907449.json -o HMA_Config_1759302907449.patched.json
```

if you want to overwrite your config of HAM, run command below in your termux (Root needed) \
`app_id` is the app id of HAM, like `org.frknkrc44.hma_oss`, `com.tsng.hidemyapplist` \
`-o \~` to overwrite config file

```sh
sudo python ./HMA_rewriter.py -c /data/data/<app_id>/files/config.json -o \~
```

example
```sh
sudo python ./HMA_rewriter.py -c /data/data/org.frknkrc44.hma_oss/files/config.json -o \~
```

to merge whitelists for whitelist-enabled-apps, use `--merge`


## Ignore Rules
to simply ignore some apps while applying a template, use `-i <APPID>` or `--ignore <APPID>`

if you want to ignore apps dynamically, follow these rules:
1. `-i <APPID>` like `-i org.frknkrc44.hma_oss` to ignore app with app id `org.frknkrc44.hma_oss`
2. `-i #<APP_LIST>` like `-i #cnapps` to ignore all apps in the app list (also *template* in HMA app) `cnapps` (either blacklist or whitelist)
3. `-i <IGNORE_RULES_FILE>` like `-i /path/to/ignore.rules` to load ignore rules file in which each line is one of the ignore rules

### Ignore Rules File
NOTE: use `//` to add a comment

```text
org.frknkrc44.hma_oss  // Hide-My-Applist app
#cnapps  // app list for cn apps
/path/to/another/ignore.rules  // another ignore rules file
// you can also add new rules at bottom
```
