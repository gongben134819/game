# Android 打包说明

本项目的 Android 目标是横屏 debug APK。运行时代码仍基于 Pygame，打包工具链使用 Buildozer 和 python-for-android。

## 环境要求

- Linux、WSL2 或 Docker 环境。
- Python 3、JDK、Android SDK/NDK、Buildozer。
- Windows 主机可编辑项目，但不建议直接在原生 Windows 上运行 Buildozer。

## 构建命令

```bash
python -m pip install buildozer
buildozer android debug
```

构建成功后，APK 通常位于 `bin/` 目录。

## 已包含内容

- `main.py`
- `game/`
- `assets/`
- `data/*.example.json`

真实运行时存档 `data/save_data.json` 和 `data/settings_data.json` 不会打入初始包。

## 常见阻塞点

- python-for-android 的 Pygame 支持依赖 SDL2 bootstrap 和可用 recipe。
- 如果 `requirements = python3,pygame` 在当前 p4a 版本失败，保留完整失败日志，并优先检查 pygame recipe、SDL2 bootstrap 和 NDK/API 版本。
- 本期不处理正式签名、上架、隐私政策和支付能力。
