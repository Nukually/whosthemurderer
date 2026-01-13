# Who's the Murderer (MVP)

局域网单房间剧本杀桌面应用。房主同时运行服务器与客户端，玩家通过局域网连接并同步房间状态。当前为 MVP，聚焦基础联机、角色分配、阅读/搜证/投票/复盘展示。

## Features
- TCP JSON 行协议联机，单房间模式
- 房主控制：选剧本、设置人数（4–6）、分配角色、推进阶段
- 玩家端：查看角色剧本、搜证、投票、结果复盘
- 本地脚本文件加载（`data/scripts/`）

## Project Structure
- `backend/`: 服务器与房间状态
- `frontend/`: PyQt5 客户端界面
- `data/scripts/`: 剧本 JSON 文件
- `tests/`: 预留（尚未配置测试框架）
- `assets/`: 预留资源目录

## Requirements
- Python 3.9+
- Windows 桌面环境（MVP 面向 Windows）

## Setup
```bash
pip install -r requirements.txt
```

## Run
```bash
python -m frontend.main
```

## Script Format
剧本示例位于 `data/scripts/sample-script.json`。基本结构如下：
```json
{
  "id": "script_001",
  "title": "剧本标题",
  "summary": "一句话概述",
  "roles": [
    { "id": 1, "name": "角色名", "intro": "公共介绍", "story": "角色视角剧本" }
  ],
  "events": [
    { "id": "e1", "time": "21:40", "content": "事件描述" }
  ],
  "clues": [
    { "id": "c1", "name": "线索名", "type": "normal", "content": "线索内容" }
  ],
  "truth": "真相与复盘内容"
}
```

## Notes
- 单房间模式，无账号/数据库/语音聊天。
- 玩家可改名；身份牌和公共介绍对所有人可见。
