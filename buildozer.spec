[app]
title = Tracker
package.name = tracker
package.domain = org.tracker
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy==2.3.1,https://github.com/KivyMD/KivyMD/archive/master.zip,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 30
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
android.debug_artifact = apk
android.release_artifact = apk
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1