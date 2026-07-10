[app]
title = 金币冲刺
package.name = coinrush
package.domain = org.coinrush

source.dir = .
source.include_exts = py,png,jpg,wav,json
source.include_patterns = assets/*,assets/images/*,assets/sounds/*,game/*,game/config/*,game/core/*,game/entities/*,game/systems/*,game/ui/*,data/*.example.json
source.exclude_patterns = .git/*,.idea/*,.env-backup-*/*,__pycache__/*,*/__pycache__/*,build/*,dist/*,release/*,.buildozer/*,data/save_data.json,data/settings_data.json

version = 0.1.0
requirements = python3,pygame
orientation = landscape
fullscreen = 1
icon.filename = assets/images/logo.jpg

android.permissions =
android.wakelock = True
android.api = 35
android.minapi = 23
android.archs = arm64-v8a
android.accept_sdk_license = True
android.blacklist_src = android/blacklist.txt

[buildozer]
log_level = 2
warn_on_root = 0
