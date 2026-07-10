# 金币冲刺项目结构

本项目按职责拆分文件，入口保持在根目录，游戏逻辑集中放入 `game/` 包中，资源、运行数据、工具脚本和测试分别独立存放。

## 目录说明

- `main.py`：游戏启动入口，只负责初始化窗口、图标和主循环。
- `game/config/`：全局配置，例如窗口尺寸、资源路径、数值常量。
- `game/core/`：核心流程控制，例如关卡状态、刷新节奏、碰撞结算和界面调度。
- `game/entities/`：实体对象，例如玩家、敌人、金币和掉落物。
- `game/systems/`：通用系统，例如资源加载、存档、升级、武器和表现反馈。
- `game/ui/`：菜单、商店、HUD、升级卡片和结算界面绘制。
- `assets/images/`：图片素材。
- `assets/sounds/`：音效素材。
- `data/`：运行时数据；真实 `save_data.json` 不提交，仓库只保留默认结构样例。
- `scripts/`：项目辅助脚本，例如生成像素素材和音效。
- `tests/`：自动化测试。

## 维护约定

- 新玩法流程优先放在 `game/core/`，避免把主循环逻辑写进 `main.py`。
- 新角色、敌人、掉落物等游戏对象优先放在 `game/entities/`。
- 新武器、升级、存档、资源加载、粒子反馈等可复用机制优先放在 `game/systems/`。
- 新界面绘制或鼠标交互优先放在 `game/ui/`。
- 新素材统一放入 `assets/images/` 或 `assets/sounds/`，并继续保留资源缺失回退。
- 存档结构变更时同步更新 `data/save_data.example.json`，不要提交本机真实游玩存档。
- 运行时产生的缓存、临时文件和本机环境备份不提交到项目源码中。

## 常用命令

```powershell
python -m py_compile main.py game\config\settings.py game\core\level.py game\entities\coin.py game\entities\drop.py game\entities\enemy.py game\entities\player.py game\systems\effects.py game\systems\resources.py game\systems\save_data.py game\systems\upgrades.py game\systems\weapons.py game\ui\ui.py scripts\generate_assets.py tests\test_systems.py
python -m unittest discover -s tests -v
python scripts\generate_assets.py
```

## 打包发布

Windows 安装包和便携包使用 PyInstaller one-folder 作为基础产物，构建依赖单独放在 `requirements-build.txt`，不会加入游戏运行依赖。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Version 0.1.0
```

构建完成后：

- 可运行目录：`dist\金币冲刺\金币冲刺.exe`
- 便携包：`release\金币冲刺-portable-0.1.0.zip`
- 安装包：`release\金币冲刺-setup-0.1.0.exe`

安装包需要本机安装 Inno Setup 6。若未安装，脚本会跳过安装包步骤，但仍会生成 PyInstaller 目录和便携包。

Android debug APK 使用 Buildozer，建议在 Linux、WSL2 或 Docker 环境执行：

```bash
python -m pip install buildozer
buildozer android debug
```

Android 打包说明见 `android/README.md`。真实运行时存档 `data/save_data.json` 和 `data/settings_data.json` 不会进入初始发布包。

打包版首次运行会在用户数据目录创建真实存档和设置文件，Windows 下默认为 `%APPDATA%\CoinRush\`，避免安装到 `Program Files` 后因为目录权限导致无法保存进度。
