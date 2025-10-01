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
