from typing import List

ANALYZE_PROMPT = """你是一个代码审查专家。请分析以下代码变更是否完整实现了需求功能。

## 需求文档
{requirement_doc}

## 代码变更
{code_diff}

## 分析要求
请从以下维度进行分析，并以JSON格式返回结果：
1. 需求覆盖率分析 - 逐条检查每个需求点是否在代码中实现
2. 夹带检测 - 检查是否存在与需求无关的代码变更
3. 语法检查 - 检查代码是否存在语法错误
4. 边界场景 - 检查是否处理了边界条件
5. 异常兜底 - 检查是否有容错机制
6. 代码质量 - 检查命名规范、潜在bug等

返回JSON格式，包含requirements数组、issues数组、coverage_percent和summary。
"""

CONTEXT_SELECTION_PROMPT = """分析以下代码变更，告诉我需要读取哪些额外的文件才能完整理解这些变更。

## 变更文件列表
{changed_files}

## 代码diff
{diff}

返回JSON格式: {"required_files": ["file1.py", ...], "reason": {...}}
最多选择5个文件。
"""

def build_analyze_prompt(requirement_doc: str, code_diff: str) -> str:
    return ANALYZE_PROMPT.format(requirement_doc=requirement_doc, code_diff=code_diff)

def build_context_selection_prompt(changed_files: List[str], diff: str) -> str:
    return CONTEXT_SELECTION_PROMPT.format(changed_files="\n".join(changed_files), diff=diff)
