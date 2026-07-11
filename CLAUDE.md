# Claude Working Rules

## Project Goal

本项目是一个 AI Data Analyst Agent。

所有开发必须遵循 plan.md 和 roadmap.md。

不得自行增加新功能。

---

## Development Rule

一次只开发当前 Branch 对应的 Feature。

禁止：

- 修改其它模块
- 修改 roadmap
- 修改 plan
- 修改 README
- 重构无关代码

---

## Coding Rule

遵循：

- Ruff
- Black
- Type Hint

所有 Public Function 必须写 Docstring。

---

## Git Rule

不要 Commit。

不要 Push。

不要 Merge。

所有 Git 操作由开发者完成。

---

## Response Rule

每次修改前：

先说明：

1. 要修改哪些文件
2. 为什么修改
3. 修改完成后的影响

如果超出当前任务：

必须停止并说明。

---

## Completion Rule

完成当前任务后，请不要继续实现 Roadmap 中的下一个功能。

如果当前 Feature 已完成，请停止，并等待新的任务。
