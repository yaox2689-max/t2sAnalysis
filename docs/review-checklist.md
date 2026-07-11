# PR Review Checklist

> 每个 PR 合并前，逐项检查。全部勾选后方可 Merge。

---

## 1. Scope

- [ ] 只修改 Task 指定文件
- [ ] 没有修改无关模块

## 2. Architecture

- [ ] 符合 `architecture.md`
- [ ] 没有跨层调用（如 Database 依赖 Agent）
- [ ] 基础设施层不包含业务逻辑
- [ ] Config 为唯一配置来源

## 3. Code Review

- [ ] 架构符合设计文档
- [ ] 无重复代码
- [ ] 无 TODO / FIXME
- [ ] 类型注解正确
- [ ] Public Function 有 Docstring

## 4. Functional Test

- [ ] Database 连通正常
- [ ] Redis 连通正常
- [ ] Config 读取正确
- [ ] Ruff/Black 通过
- [ ] 单元测试通过

## 5. Negative Test

- [ ] 数据库关闭时 health() 返回 False 而非崩溃
- [ ] Redis 关闭时操作返回友好错误
- [ ] 删除不存在的 key 返回 False 而非异常
- [ ] 配置错误时错误信息清晰

## 6. Git Review

```bash
git diff --stat master...HEAD
```

- [ ] 修改文件数量合理
- [ ] 无临时文件（`.pyc`、`__pycache__`、`.idea/`、`.vscode/`）
- [ ] 无调试代码
- [ ] Commit Message 描述准确

---

## Review Decision

```markdown
Status: ✅ Approved / ❌ Changes Requested

Reason:
- ...

Next:
- Merge PR #{number}
- Start feature/{next-branch}
```
