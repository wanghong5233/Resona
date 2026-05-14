# Training Pipeline (Safe + Practical)

本目录用于执行 Resona 的数据构造、清洗、SFT 与 DPO 训练。

## 执行位置（先看）

### 本地电脑（推荐执行）
- 只做：数据采集、脱敏、构造、清洗、质检报告。
- 不做：SFT/DPO 训练（避免本地安装大模型训练依赖）。

### 云端 4090（推荐执行）
- 只做：SFT + DPO 训练、评测与导出。

你的本地配置（32GB 内存、16 核 CPU）做数据流水线是足够的。

## 安全说明（必须读）

- `training/data_generation/redbook_crawler/xiaohongshu_mcp.py` 原始工具包含发布评论能力。  
  现在已加默认只读开关：`XHS_READ_ONLY_MODE=1`。
- 训练数据采集请使用 **只读脚本**：`training/data_generation/safe_collect_from_xhs.py`。
- 只用于学习和研究，遵守平台规则与法律法规，控制频率，避免高并发与过量采集。

## 1) 本地依赖安装（轻量）

> 不会安装 torch / CUDA / 训练大包。

```bash
pip install -r training/requirements.txt
playwright install chromium
```

## 2) 云端训练依赖安装（4090）

```bash
# 如云端镜像已带 torch/cuda，可直接装 Llama-Factory
pip install "llamafactory[metrics]"

# 若云端未带 torch，请按云环境 CUDA 版本安装对应 torch（略）
```

## 3) 环境变量（数据构造/清洗）

### Windows PowerShell

```powershell
$env:TEACHER_API_KEY = "你的Key"
$env:TEACHER_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:TEACHER_MODEL = "qwen-plus"
```

### Linux/macOS

```bash
export TEACHER_API_KEY="你的Key"
export TEACHER_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export TEACHER_MODEL="qwen-plus"
```

## 4) 准备样例文件

```bash
cp training/data/raw/keywords.example.txt training/data/raw/keywords.txt
cp training/data/raw/eval_cases.example.jsonl training/data/raw/eval_cases.jsonl
```

### Windows PowerShell 等价命令

```powershell
Copy-Item training\data\raw\keywords.example.txt training\data\raw\keywords.txt
Copy-Item training\data\raw\eval_cases.example.jsonl training\data\raw\eval_cases.jsonl
```

## 5) 本地数据流水线（先跑完）

### ⚠️ 重要：Schema 变更与旧数据清理

当前采集**只输出评论区对话对**（`dialogue_pairs`），不再包含 `title`/`content`/`comments`。若存在此前采得的旧格式 `xhs_candidates.jsonl` 或 `anchors.jsonl`，**请先删除**再重新跑流水线，否则 `extract_anchor_pairs` 会跳过（无 `dialogue_pairs`）。详见 `training/data/DATA_SCHEMA.md`。

### 5.0 快速验证（建议先跑）

```powershell
# 删除旧数据（如有）
Remove-Item training/data/raw/xhs_candidates_smoke.jsonl -ErrorAction SilentlyContinue
Remove-Item training/data/raw/xhs_candidates.jsonl -ErrorAction SilentlyContinue

# 快速采集（约 5–8 条笔记，1–2 分钟）
python training/data_generation/safe_collect_from_xhs.py --keywords-file training/data/raw/keywords.txt --output training/data/raw/xhs_candidates_smoke.jsonl --max-notes-per-keyword 3 --max-total-urls 10 --max-comments 8 --min-comment-likes 5 --strict-high-like --min-liked-comments-per-note 1 --page-timeout-ms 25000 --progress-every 3
```

```bash
# Linux/macOS 等价
rm -f training/data/raw/xhs_candidates_smoke.jsonl training/data/raw/xhs_candidates.jsonl
python training/data_generation/safe_collect_from_xhs.py --keywords-file training/data/raw/keywords.txt --output training/data/raw/xhs_candidates_smoke.jsonl --max-notes-per-keyword 3 --max-total-urls 10 --max-comments 8 --min-comment-likes 5 --strict-high-like --min-liked-comments-per-note 1 --page-timeout-ms 25000 --progress-every 3
```

然后验证：

```bash
python training/scripts/report_high_like_coverage.py --input-jsonl training/data/raw/xhs_candidates_smoke.jsonl --like-threshold 5
```

### 5.1 只读采集候选

> **数据量依据**：SFT 需 3200 训练 + 320 验证，锚点需 600-1000 条，对应约 **2000-4000 条 dialogue_pairs**。每笔记约 2-5 对，目标 2000 URL、成功率 50% 时约得 2000+ 对。
>
> **增量实时保存**：每条 kept 后立即 `flush`，中断不丢数据；重跑加 `--append` 按 note_id 去重续采。

**正式采集（首次）：**

```powershell
python training/data_generation/safe_collect_from_xhs.py --keywords-file training/data/raw/keywords.txt --output training/data/raw/xhs_candidates.jsonl --max-notes-per-keyword 80 --max-total-urls 2000 --max-comments 8 --min-comment-likes 10 --strict-high-like --min-liked-comments-per-note 1 --page-timeout-ms 45000 --sleep-sec 1.5 --progress-every 20 --drop-ads
```

**断点续采（中断后追加）：**

```powershell
python training/data_generation/safe_collect_from_xhs.py --keywords-file training/data/raw/keywords.txt --output training/data/raw/xhs_candidates.jsonl --append --max-notes-per-keyword 80 --max-total-urls 2000 --max-comments 8 --min-comment-likes 10 --strict-high-like --min-liked-comments-per-note 1 --page-timeout-ms 45000 --sleep-sec 1.5 --progress-every 20 --drop-ads
```

```bash
# Linux/macOS 等价（首次）
python training/data_generation/safe_collect_from_xhs.py --keywords-file training/data/raw/keywords.txt --output training/data/raw/xhs_candidates.jsonl --max-notes-per-keyword 80 --max-total-urls 2000 --max-comments 8 --min-comment-likes 10 --strict-high-like --min-liked-comments-per-note 1 --page-timeout-ms 45000 --sleep-sec 1.5 --progress-every 20 --drop-ads

# 断点续采：在上述命令末尾加 --append

### 5.1b 高赞覆盖率验证（建议立即跑）

```bash
python training/scripts/report_high_like_coverage.py --input-jsonl training/data/raw/xhs_candidates.jsonl --like-threshold 10 --top-k 5
```

### 5.2 抽取锚点

```bash
python training/data_generation/extract_anchor_pairs.py --input-jsonl training/data/raw/xhs_candidates.jsonl --output-jsonl training/data/raw/anchors.jsonl --max-records 1200
```

### 5.3 生成 SFT 候选

```bash
python training/data_generation/build_sft_dataset.py --anchors-jsonl training/data/raw/anchors.jsonl --output-jsonl training/data/processed/sft_candidates.jsonl --target-per-combo 40 --max-total 3600
```

### 5.4 清洗 + 切分

```bash
python training/data_generation/filter_sft_dataset.py --input-jsonl training/data/processed/sft_candidates.jsonl --train-out training/data/processed/sft_train.jsonl --val-out training/data/processed/sft_val.jsonl --report-out training/reports/data_qc_report.md --enable-judge
```

### 5.5 构造 DPO 偏好对

```bash
python training/data_generation/build_dpo_dataset.py --sft-train-jsonl training/data/processed/sft_train.jsonl --train-out training/data/processed/dpo_train.jsonl --val-out training/data/processed/dpo_val.jsonl --max-prompts 1000 --max-pairs 1000 --min-gap 1.5
```

### 5.6 训练前体检（强烈建议）

```bash
python training/scripts/preflight_check.py
```

## 6) 云端 4090 训练（先 smoke，再全量）

```bash
bash training/scripts/run_sft_smoke.sh
bash training/scripts/run_sft.sh
bash training/scripts/run_dpo_smoke.sh
bash training/scripts/run_dpo.sh
```

## 7) 固定样例评测（Base/SFT/DPO）

```bash
python training/scripts/evaluate_fixed_cases.py --cases-jsonl training/data/raw/eval_cases.jsonl --report-md training/reports/model_eval_report.md --base-url http://127.0.0.1:8001/v1 --api-key EMPTY --model-base Qwen/Qwen2.5-7B-Instruct --model-sft your-sft-model-id --model-dpo your-dpo-model-id
```

