[app]

title = Tracker
package.name = tracker
package.domain = org.tracker
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
; Kivy 2.3.x + стабильный релиз KivyMD 1.2.0 (в нём есть MDTabsBase, MDTabs, MDTopAppBar).
; НЕ используйте archive master.zip из GitHub — он меняется со временем и ломает воспроизводимую сборку.
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
; Для debug-артефакта значение должно быть булевым (True), а не строкой "apk"
android.debug_artifact = True
android.release_artifact = apk
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
