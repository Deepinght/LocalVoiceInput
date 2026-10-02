from PyInstaller.utils.hooks import collect_all
from pathlib import Path

datas, binaries, hiddenimports = [], [], []
for package in ('sherpa_onnx', 'lupa', 'sounddevice'):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h
# Explicit public resources only: never bundle local corrections or user scripts.
datas += [(str(Path('config') / name), 'config') for name in ('default.yaml', 'profiles.yaml', 'models.yaml')]
datas += [(str(Path('dictionaries') / name), 'dictionaries') for name in ('common.yaml', 'science.yaml', 'chemistry.yaml', 'units.yaml')]
datas += [('lua/builtin', 'lua/builtin'), ('templates', 'templates')]
a = Analysis(['src/voiceinput/__main__.py'], pathex=['src'], binaries=binaries,
    datas=datas, hiddenimports=hiddenimports + ['pythoncom', 'pywintypes', 'win32timezone'],
    excludes=['pytest'], noarchive=False)
# Qt 6.11 uses the Windows ICU API. A third-party ICU from PATH (for example
# Poppler's version-suffixed ICU) is ABI-incompatible; use the OS implementation.
a.binaries = [entry for entry in a.binaries if entry[0].lower() not in ('icuuc.dll', 'icudt78.dll')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='VoiceInput',
    console=False, debug=False, contents_directory='runtime')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='VoiceInput')
