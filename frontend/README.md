# 工安卫士 · 前端演示系统

石油井场安全培训系统的**纯 mock 前端演示**：不依赖任何真实后端，所有数据位于 `src/mock`，api 层（`src/api`）保留真实接口形状，可平滑替换为 FastAPI 后端。

## 技术栈

Vue 3.5 + Vite 5 + TypeScript（严格模式，禁 any）+ Pinia + Vue Router + Tailwind CSS 3 + Element Plus + ECharts 5 + Axios

## 安装与运行

```bash
# 安装依赖（国内环境建议使用 npmmirror）
npm install --registry=https://registry.npmmirror.com

# 启动开发服务器（http://localhost:5174）
npm run dev

# 类型检查 + 生产构建
npm run build

# 预览生产构建
npm run preview
```

## 演示账号

| 角色 | 账号 | 密码 | 能力 |
| --- | --- | --- | --- |
| 工人 | `zhangjg`（张建国 · 司钻） | `123456` | 安全问答 / 考试 / 成绩 |
| 管理员 | `admin`（刘安全） | `123456` | 运维仪表盘 + 全部管理页 |

登录页支持一键登录（JWT mock，2h 有效，localStorage 持久化，登出模拟 Redis 黑名单提示）。

## 页面地图

- `/login` 登录（角色切换、演示账号、架构演示入口）
- `/architecture` 系统架构演示（单 Agent 多工作流 / 四级缓存 / 混合检索 / 权限三层闭环 / LLM 三层降级）
- `/worker/home` 工人首页 · `/worker/chat` 安全问答（SSE 逐字 + 8 步检索流）· `/worker/exams` 考试列表 · `/worker/exams/:id/take` 答题（倒计时/自动保存/幂等提交）· `/worker/exams/:id/result` 成绩详情（环形图 + rubric 雷达 + 错题解析）
- `/admin/dashboard` 运维仪表盘 · `documents` 文档 · `faq` FAQ · `users` 用户权限 · `question-bank` 题库与 AI 出卷 · `graph` 知识图谱 · `audit` 审计日志 · `eval` RAGAS 评测

## 问答演示要点（`/worker/chat`）

1. 推荐问题命中四类缓存：`Redis 精确命中` / `语义缓存 0.90` / `FAQ 0.86` / `完整 RAG`；
2. 发送后展示检索步骤流：查询理解 → 缓存查找 → FAQ → 记忆检索 → 工具规划 → 并行执行 → 质量门控 → 结果融合（缓存命中时自动短路跳步）；
3. 回答带 `[1]` 引用徽标，下方展开引用来源卡（文档名 / 章节 / 片段 / 相关度 / public·internal）与知识图谱关系链；
4. 「查看机密岗位文件」演示 403 权限兜底；「提示词注入演示」触发安全守卫拦截；
5. route 标签展示 LLM 路由：`qwen-flash` / `qwen-plus` / `mock 兜底`。

## 目录结构

```
src/
├── api/          # 接口层（真实接口形状 + mock 实现，替换后端只改这里）
├── mock/         # SSE 模拟器 + 全部演示数据
├── stores/       # Pinia：auth / qa / exam / admin
├── router/       # 路由 + 登录守卫 + admin 守卫
├── layouts/      # WorkerLayout（移动优先）/ AdminLayout（深色侧边栏）
├── components/   # common（骨架/空态/重试/徽章/步骤流）· qa（气泡/引用/图谱链）· charts（ECharts 封装）
├── views/        # Login / Architecture / worker×5 / admin×8
├── styles/       # 设计系统（深蓝 #0B1F33 · 安全橙 #FF7A1A · 青绿 #14B8A6）
├── types.ts      # 全局领域类型（唯一类型源）
└── utils/        # 轻量 Markdown 渲染
```

## 说明

- 所有列表页具备骨架屏 / 空状态 / 错误重试；
- 考试提交模拟幂等锁（Redis SETNX + DB 唯一约束），重复提交返回同一成绩；
- 答题进度自动写入 localStorage，刷新不丢；
- 工人端 375px 起步，管理端 1440px 最佳。
