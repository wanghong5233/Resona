# Safety Notice

当前 `xiaohongshu_mcp.py` 是一个“搜索 + 分析 + 发布评论”的综合工具，包含以下高风险函数：

- `post_smart_comment()`
- `post_comment()`

在本项目的数据构造流程中，**不要调用任何发布或互动函数**。  
请改用仓库新增的只读脚本：

- `training/data_generation/safe_collect_from_xhs.py`

该脚本仅用于采集公开可见文本，不执行评论、点赞、关注等行为。

# Safety Notice

当前 `xiaohongshu_mcp.py` 是一个“搜索 + 分析 + 发布评论”的综合工具，包含以下高风险函数：

- `post_smart_comment()`
- `post_comment()`

在本项目的数据构造流程中，**不要调用任何发布或互动函数**。  
请改用仓库新增的只读脚本：

- `training/data_generation/safe_collect_from_xhs.py`

该脚本仅用于采集公开可见文本，不执行评论、点赞、关注等行为。

