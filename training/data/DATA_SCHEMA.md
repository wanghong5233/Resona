# 数据 Schema 说明

## 采集输出 (xhs_candidates.jsonl)

**只采评论区，不采正文。** 每条记录结构：

```json
{
  "platform": "xiaohongshu",
  "url": "https://...",
  "dialogue_pairs": [
    {
      "input": "父评论内容",
      "output": "高赞回复内容",
      "output_likes": 50,
      "output_likes_raw": "50",
      "source": "api_reply_edge",
      "thread_depth": 1,
      "thread_root": "根评论内容（可选）"
    }
  ],
  "pair_stats": {
    "selection_mode": "api",
    "like_signal_found": true,
    "total_pairs": 3,
    "high_like_pairs": 3,
    "min_reply_likes": 5
  },
  "source_keywords": ["职场拒绝", "..."],
  "collected_at": "2026-03-01T12:00:00.000000Z",
  "fetch_meta": { "input_url": "...", "final_url": "...", "http_status": 200 }
}
```

### dialogue_pairs 字段与类型

| 字段 | 类型 | 含义 | 下游用途 |
|------|------|------|----------|
| `input` | string | 父评论内容（一级评论） | 场景归纳、instruction 构造 |
| `output` | string | 高赞回复（二级评论），高情商体现 | anchor_reply、训练 target |
| `output_likes` | **int** | 点赞数（已解析为整数） | **排序、过滤阈值** |
| `output_likes_raw` | string | 原始显示值（如 "1.2万"） | 展示、日志 |
| `source` | string | `api_reply_edge` / `dom_parent_reply` / `dom_nested_reply` | 质量分层、统计 |
| `thread_depth` | int(可选) | 回复层级（1=父评->子评，2=子评->子子评） | 嵌套对话分析 |
| `thread_root` | string(可选) | 根评论文本（API 可用时提供） | 线程聚类/去重 |

### 下游支持操作

- **按点赞排序**：`sorted(pairs, key=lambda p: p["output_likes"], reverse=True)`
- **按阈值过滤**：`[p for p in pairs if p["output_likes"] >= min_likes]`
- **按 source 分层**：优先 `api_reply_edge` > `dom_parent_reply` > `dom_nested_reply`

### 质量约束（采集时已过滤）

- `output` 长度 ≥ 10 字
- 排除纯 `@xxx`、纯 `[xxxR]` 表情占位符
- `output_likes` 为 int，`output_likes_raw` 可能为 "1.2万" 等，排序以 `output_likes` 为准

### 一对多关系与多轮嵌套

一个父评论可对应多个高赞子回复，每条为独立项；若存在多轮嵌套回复，可额外产出 `thread_depth>=2` 的边。

### 旧 Schema（已废弃）

`title`、`content`、`comments`。旧格式请删除后重采。

---

## 下游格式

- **anchors.jsonl**：`extract_anchor_pairs` 从 `dialogue_pairs` 抽取 `(context, anchor_reply)`，依赖 `input/output/output_likes`
- **sft_candidates.jsonl**：`instruction/input/output`
- **filter_sft_dataset**：读 sft_candidates，结构不变
