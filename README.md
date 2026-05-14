# Resona —— 基于 MBTI 约束的高情商社交 AI 助手

**核心理念：** "Optimization at Natural Frequency"  
在用户的 MBTI 固有频率（人格特质）上，寻找社交表达的最优解，而非强迫用户伪装成另一个人。

---

## 🎯 项目简介

Resona 是一款基于大模型微调 (SFT + DPO) 与 MBTI 人格心理学的智能社交助手，旨在**不改变用户真实人格**的前提下，帮助用户在职场、亲密关系等高压社交场景中，生成**成熟、得体且有边界感**的高情商回复，并对 PUA、诈骗等恶意对话进行实时预警。

### 一句话价值主张

> **"让每个 INTJ 都能像成熟的 INTJ 一样说话，而不是装成 ENFP。"**

---

## 🚀 快速开始

### 前置要求

- **Python**: 3.11+
- **Node.js**: 20+
- **Docker Desktop**: 最新版
- **Git**: 2.0+

### 开发环境启动

```bash
# 1. 启动 Backend（Docker 热重载）
make up

# 2. 启动 Frontend（Vite HMR）
cd frontend
npm install
npm run dev

# 3. 浏览器访问
# http://localhost:5173
```

---

## 📁 项目结构

```
resona/
├── backend/              # FastAPI 后端服务
│   ├── api/             # API 层（路由）
│   ├── services/        # Service 层（业务逻辑）
│   ├── adapters/        # Adapter 层（外部服务封装）
│   ├── schemas/         # Pydantic 数据模型
│   ├── core/            # 核心工具（日志、异常、枚举）
│   ├── data/            # 配置文件（Prompt模板、安全关键词）
│   ├── models/          # 数据库模型（ORM，为未来预留）
│   └── tests/           # 单元测试
├── frontend/            # React + Vite 前端
│   └── src/
│       ├── pages/       # 页面组件
│       ├── components/  # UI 组件
│       ├── api/         # API 调用封装
│       ├── store/       # 状态管理（Valtio）
│       ├── router/      # 路由配置
│       ├── types/       # TypeScript 类型定义
│       ├── utils/       # 工具函数
│       └── data/        # 静态数据（MBTI 测试题库）
├── desktop/             # Electron 桌面应用
│   ├── main/            # 主进程（托盘、快捷键、剪贴板）
│   ├── preload/         # 预加载脚本
│   └── resources/       # 资源文件（图标）
├── training/            # 模型训练流水线
│   ├── data_generation/ # 数据生成脚本
│   ├── data/            # 训练数据集
│   ├── configs/         # 训练配置（SFT/DPO）
│   ├── scripts/         # 训练脚本
│   └── outputs/         # 模型权重输出
├── inference_service/   # LLM 推理服务（独立部署）
├── docker-compose.yml   # Docker 开发环境配置
├── Makefile             # 项目管理命令
└── README.md            # 项目说明（本文件）
```

---

## 🏗️ 核心架构

### 三层架构设计

```
API 层 (FastAPI)
    ↓
Service 层 (业务逻辑编排)
    ↓
Adapter 层 (外部服务封装)
    ├─ LLM Adapter (支持多后端切换)
    ├─ Cache Adapter (Redis)
    └─ Config Adapter (YAML/JSON)
```

### LLM 后端切换（一行配置）

```yaml
# config.yaml
llm:
  backend: "gpt4"        # Week 1-3: GPT-4 API
  # backend: "qwen"      # Week 3-4: 开源模型
  # backend: "finetuned" # Week 4-5: 自训练模型
```

---

## 🛠️ Makefile 命令

```bash
make up              # 启动所有服务（Backend + Redis）
make down            # 停止所有服务
make logs-backend    # 查看后端日志
make shell-backend   # 进入后端容器
make redis-cli       # 进入 Redis CLI
make ps              # 查看服务状态
```

---
## 🎯 MVP 功能

- ✅ 回复生成（支持 4 种 MBTI：INTJ / ENFP / ISTJ / ESFP）
- ✅ 场景适配（职场 / 亲密关系）
- ✅ 风险预警（PUA / 诈骗 / 情绪勒索）
- ✅ MBTI 测试（10 题快速版）
- ✅ 系统托盘 + 全局快捷键（`Ctrl+Shift+R`）
- ✅ 剪贴板集成

---

## 🔧 技术栈

### Backend
- **框架**: FastAPI
- **LLM**: OpenAI API / Qwen2.5-7B / 自训练模型
- **缓存**: Redis
- **日志**: Loguru
- **配置**: Pydantic Settings + YAML

### Frontend
- **框架**: React 18 + Vite 6 + TypeScript
- **UI**: Ant Design 5
- **状态管理**: Valtio
- **HTTP**: Axios
- **路由**: React Router

### Desktop
- **框架**: Electron
- **打包**: electron-builder

### Training
- **框架**: Llama-Factory
- **模型**: Qwen2.5-7B-Instruct + QLoRA
- **推理**: vLLM

---

## 📄 License

MIT License


