# Third-party notices

VoiceInput itself is licensed under the MIT License. See [LICENSE](LICENSE).

VoiceInput uses and, in the Windows release, redistributes third-party software. Those components are not relicensed under the VoiceInput MIT License. Each component remains subject to its own copyright and license terms. The list below describes the direct runtime dependencies and the principal native components included by them in VoiceInput V0.2.1.

## Components included in the Windows release

| Component | Version in V0.2.1 | License | Project |
|---|---:|---|---|
| Python | 3.13 | Python Software Foundation License | https://www.python.org/ |
| PySide6, Qt for Python, Shiboken6 and Qt 6 libraries/plugins | 6.11.2 | LGPL-3.0-only, with GPL/commercial alternatives offered by the copyright holder | https://www.qt.io/qt-for-python |
| sherpa-onnx and sherpa-onnx-core | 1.13.8 | Apache-2.0 | https://github.com/k2-fsa/sherpa-onnx |
| ONNX Runtime, redistributed through sherpa-onnx | bundled with sherpa-onnx | MIT | https://github.com/microsoft/onnxruntime |
| NumPy and its bundled native libraries | 2.5.3 | BSD-3-Clause and additional notices contained in NumPy's license directory | https://numpy.org/ |
| python-sounddevice | 0.5.6 | MIT | https://python-sounddevice.readthedocs.io/ |
| PortAudio, redistributed through python-sounddevice | bundled with sounddevice | MIT | https://www.portaudio.com/ |
| Lupa | 2.8 | MIT-style license | https://github.com/scoder/lupa |
| Lua and LuaJIT runtimes, redistributed through Lupa | bundled with Lupa | MIT | https://www.lua.org/ and https://luajit.org/ |
| PyYAML | 6.0.3 | MIT | https://pyyaml.org/ |
| cffi and pycparser | 2.1.1 / 3.0 | MIT / BSD-3-Clause | https://cffi.readthedocs.io/ and https://github.com/eliben/pycparser |
| pywin32 | 312 | Python Software Foundation License | https://github.com/mhammond/pywin32 |
| OpenSSL libraries used by the packaged Python/Qt runtime | 3.x | Apache-2.0 | https://www.openssl.org/ |
| SQLite | bundled with Python | Public domain | https://www.sqlite.org/ |
| PyInstaller bootloader | 6.22.3 | GPL-2.0-or-later with the PyInstaller bootloader exception | https://pyinstaller.org/ |
| Microsoft Visual C++ runtime libraries | redistributable runtime | Microsoft Software License Terms | https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist |

Where a Python wheel supplies its own license directory, the Windows release retains that directory under `runtime/<package>.dist-info/licenses/`. NumPy's directory also contains the notices for native code bundled in NumPy.

### Qt / PySide6 notice

The Windows release uses Qt and PySide6 under the GNU Lesser General Public License version 3. Qt and Shiboken are kept as separate dynamically loaded DLLs and Python extension modules in the `runtime` directory. VoiceInput does not prohibit replacement of interface-compatible LGPL libraries or reverse engineering for the purpose of debugging modifications to those libraries.

The GNU GPL version 3 and GNU LGPL version 3 texts accompanying the release are in:

- `LICENSES/GPL-3.0.txt`
- `LICENSES/LGPL-3.0.txt`

Corresponding upstream source code for the exact PySide6/Qt release can be obtained from the Qt for Python project and Qt source archives:

- https://code.qt.io/cgit/pyside/pyside-setup.git/
- https://download.qt.io/official_releases/QtForPython/
- https://download.qt.io/official_releases/qt/

## Models downloaded separately by the user

VoiceInput does not place recognition models in the source archive or Windows release. When the user starts a model download, the application retrieves these components from the sources recorded in `config/models.yaml`:

| Component | License | Project |
|---|---|---|
| SenseVoiceSmall INT8 model | Apache-2.0 | https://github.com/QwenAudio/SenseVoice |
| Silero VAD model | MIT | https://github.com/snakers4/silero-vad |

These model licenses apply to the downloaded model files. They do not change the license of the VoiceInput source code.

## Development-only tools

The development environment may install pytest, PyInstaller and their dependencies. Except for the PyInstaller bootloader embedded in the executable, development-only packages are not part of the VoiceInput source license and are not intentionally shipped as importable packages in the Windows release.

## No endorsement

Third-party project names and trademarks belong to their respective owners. Their inclusion or mention does not imply endorsement of VoiceInput. If this notice conflicts with an included third-party license text, the third-party license text controls for that component.
