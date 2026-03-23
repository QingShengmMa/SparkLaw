# 贡献指南 | Contributing Guide

感谢你考虑为 SparkLaw 做出贡献！🎉

Thank you for considering contributing to SparkLaw! 🎉

[中文](#中文) | [English](#english)

---

## 中文

### 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [问题反馈](#问题反馈)

### 行为准则

参与本项目即表示你同意遵守我们的行为准则。我们致力于为所有人提供一个友好、安全和包容的环境。

**我们的承诺**：
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

### 如何贡献

#### 🐛 报告 Bug

如果你发现了 Bug，请：

1. 检查 [Issues](https://github.com/QingShengmMa/SparkLaw/issues) 确认问题是否已被报告
2. 如果没有，创建新 Issue，包含：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为和实际行为
   - 截图（如果适用）
   - 环境信息（操作系统、浏览器、Python/Node 版本）

**Bug 报告模板**：
```markdown
**描述**
简要描述 Bug

**复现步骤**
1. 进入 '...'
2. 点击 '...'
3. 滚动到 '...'
4. 看到错误

**预期行为**
应该发生什么

**实际行为**
实际发生了什么

**截图**
如果适用，添加截图

**环境**
- OS: [e.g. Windows 11]
- Browser: [e.g. Chrome 120]
- Python: [e.g. 3.10.5]
- Node: [e.g. 18.17.0]
```

#### 💡 提出新功能

如果你有新功能的想法：

1. 检查 [Issues](https://github.com/QingShengmMa/SparkLaw/issues) 和 [Discussions](https://github.com/QingShengmMa/SparkLaw/discussions) 确认是否已有类似建议
2. 创建新 Issue 或 Discussion，包含：
   - 功能描述
   - 使用场景
   - 可能的实现方案
   - 是否愿意自己实现

#### 📝 改进文档

文档改进包括：
- 修正拼写或语法错误
- 添加缺失的文档
- 改进现有文档的清晰度
- 添加示例和教程

#### 💻 提交代码

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 进行更改
4. 运行测试和 Lint
5. 提交更改 (`git commit -m 'feat: add amazing feature'`)
6. 推送到分支 (`git push origin feature/AmazingFeature`)
7. 开启 Pull Request

### 开发流程

#### 1. 设置开发环境

**后端**
```bash
# 克隆仓库
git clone https://github.com/QingShengmMa/SparkLaw.git
cd SparkLaw

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 配置环境变量
cp .env.example .env
# 编辑 .env

# 启动后端
uvicorn app.main:app --reload
```

**前端**
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.local.example .env.local

# 启动前端
npm run dev
```

#### 2. 创建分支

分支命名规范：
- `feature/` - 新功能
- `fix/` - Bug 修复
- `docs/` - 文档更新
- `refactor/` - 代码重构
- `test/` - 测试相关
- `chore/` - 构建/工具相关

示例：
```bash
git checkout -b feature/add-voice-input
git checkout -b fix/contract-upload-error
git checkout -b docs/update-readme
```

#### 3. 编写代码

**后端代码规范**：
- 遵循 [PEP 8](https://pep8.org/) 风格指南
- 使用类型提示（Type Hints）
- 编写文档字符串（Docstrings）
- 保持函数简短和单一职责

**前端代码规范**：
- 遵循 [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- 使用 TypeScript 类型
- 组件使用函数式组件和 Hooks
- 使用 Tailwind CSS 进行样式

#### 4. 运行测试

**后端测试**
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api.py

# 生成覆盖率报告
pytest --cov=app tests/
```

**前端测试**
```bash
# 运行 Lint
npm run lint

# 修复 Lint 错误
npm run lint:fix

# 类型检查
npm run type-check
```

#### 5. 提交更改

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
# 格式
<type>(<scope>): <subject>

# 类型
feat:     新功能
fix:      Bug 修复
docs:     文档更新
style:    代码格式（不影响代码运行）
refactor: 重构
test:     测试相关
chore:    构建/工具相关
perf:     性能优化

# 示例
git commit -m "feat(chat): add voice input support"
git commit -m "fix(contract): resolve upload timeout issue"
git commit -m "docs(readme): update installation guide"
```

#### 6. 推送和创建 PR

```bash
# 推送到你的 Fork
git push origin feature/AmazingFeature

# 在 GitHub 上创建 Pull Request
```

**PR 标题格式**：
```
<type>(<scope>): <description>

示例：
feat(chat): add voice input support
fix(contract): resolve upload timeout issue
```

**PR 描述模板**：
```markdown
## 描述
简要描述这个 PR 做了什么

## 类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 代码重构
- [ ] 性能优化
- [ ] 其他

## 相关 Issue
Closes #123

## 更改内容
- 添加了 XXX 功能
- 修复了 XXX 问题
- 优化了 XXX 性能

## 测试
- [ ] 已添加单元测试
- [ ] 已通过所有测试
- [ ] 已手动测试

## 截图（如果适用）
添加截图展示更改

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 已更新相关文档
- [ ] 已添加必要的注释
- [ ] 没有引入新的警告
- [ ] 已测试所有更改
```

### 代码规范

#### Python 代码规范

```python
# 好的示例
from typing import List, Optional
from pydantic import BaseModel

class User(BaseModel):
    """用户模型
    
    Attributes:
        id: 用户 ID
        name: 用户名称
        email: 用户邮箱
    """
    id: int
    name: str
    email: Optional[str] = None

def get_user_by_id(user_id: int) -> Optional[User]:
    """根据 ID 获取用户
    
    Args:
        user_id: 用户 ID
        
    Returns:
        用户对象，如果不存在则返回 None
        
    Raises:
        ValueError: 如果 user_id 无效
    """
    if user_id < 0:
        raise ValueError("Invalid user_id")
    
    # 实现逻辑
    return None
```

#### TypeScript 代码规范

```typescript
// 好的示例
interface User {
  id: number;
  name: string;
  email?: string;
}

/**
 * 根据 ID 获取用户
 * @param userId - 用户 ID
 * @returns 用户对象或 null
 */
async function getUserById(userId: number): Promise<User | null> {
  if (userId < 0) {
    throw new Error('Invalid userId');
  }
  
  // 实现逻辑
  return null;
}

// React 组件
interface UserCardProps {
  user: User;
  onEdit?: (user: User) => void;
}

export function UserCard({ user, onEdit }: UserCardProps) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="text-lg font-semibold">{user.name}</h3>
      {user.email && <p className="text-sm text-muted-foreground">{user.email}</p>}
      {onEdit && (
        <button onClick={() => onEdit(user)}>Edit</button>
      )}
    </div>
  );
}
```

### 提交规范

#### Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**示例**：
```
feat(chat): add voice input support

- Add microphone button to chat input
- Implement speech-to-text using Web Speech API
- Add voice input settings in preferences

Closes #123
```

#### Type 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关
- `perf`: 性能优化
- `ci`: CI/CD 相关
- `build`: 构建系统相关

#### Scope 范围

- `chat`: 聊天功能
- `contract`: 合同审查
- `debate`: 模拟法庭
- `settings`: 设置
- `theme`: 主题
- `api`: API 相关
- `ui`: UI 组件
- `docs`: 文档

### 问题反馈

#### 提问前

1. 搜索现有 Issues 和 Discussions
2. 查看文档和 FAQ
3. 尝试最新版本

#### 提问时

提供以下信息：
- 清晰的问题描述
- 复现步骤
- 预期结果和实际结果
- 环境信息
- 相关日志和错误信息
- 已尝试的解决方案

### 代码审查

所有 PR 都需要经过代码审查。审查者会检查：

- 代码质量和可读性
- 是否遵循项目规范
- 测试覆盖率
- 文档完整性
- 性能影响
- 安全性

### 发布流程

1. 更新版本号（遵循语义化版本）
2. 更新 CHANGELOG.md
3. 创建 Git 标签
4. 发布 GitHub Release
5. 部署到生产环境

---

## English

### 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Commit Convention](#commit-convention)
- [Issue Reporting](#issue-reporting)

### Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. We are committed to providing a friendly, safe, and inclusive environment for everyone.

**Our Pledge**:
- Respect different viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

### How to Contribute

#### 🐛 Reporting Bugs

If you find a bug:

1. Check [Issues](https://github.com/QingShengmMa/SparkLaw/issues) to see if it's already reported
2. If not, create a new Issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots (if applicable)
   - Environment info (OS, browser, Python/Node version)

#### 💡 Suggesting Features

If you have an idea for a new feature:

1. Check [Issues](https://github.com/QingShengmMa/SparkLaw/issues) and [Discussions](https://github.com/QingShengmMa/SparkLaw/discussions)
2. Create a new Issue or Discussion with:
   - Feature description
   - Use cases
   - Possible implementation
   - Willingness to implement

#### 📝 Improving Documentation

Documentation improvements include:
- Fixing typos or grammar
- Adding missing documentation
- Improving clarity
- Adding examples and tutorials

#### 💻 Submitting Code

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Make changes
4. Run tests and lint
5. Commit changes (`git commit -m 'feat: add amazing feature'`)
6. Push to branch (`git push origin feature/AmazingFeature`)
7. Open Pull Request

### Development Workflow

#### 1. Setup Development Environment

**Backend**
```bash
git clone https://github.com/QingShengmMa/SparkLaw.git
cd SparkLaw
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

#### 2. Create Branch

Branch naming:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Tests
- `chore/` - Build/tools

#### 3. Write Code

Follow project coding standards (see [Code Standards](#code-standards))

#### 4. Run Tests

```bash
# Backend
pytest

# Frontend
npm run lint
```

#### 5. Commit Changes

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat(chat): add voice input support"
```

#### 6. Push and Create PR

```bash
git push origin feature/AmazingFeature
```

Then create a Pull Request on GitHub.

### Code Standards

- **Python**: Follow [PEP 8](https://pep8.org/)
- **TypeScript**: Follow [Airbnb Style Guide](https://github.com/airbnb/javascript)
- Use type hints/types
- Write clear comments
- Keep functions small and focused

### Commit Convention

Format: `<type>(<scope>): <subject>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style
- `refactor`: Refactoring
- `test`: Tests
- `chore`: Build/tools
- `perf`: Performance

### Issue Reporting

Before creating an issue:
1. Search existing issues
2. Check documentation
3. Try latest version

When creating an issue, provide:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment info
- Logs and errors
- Attempted solutions

---

## 🙏 感谢 | Thank You

感谢你为 SparkLaw 做出贡献！每一个贡献都让这个项目变得更好。

Thank you for contributing to SparkLaw! Every contribution makes this project better.

---

**有问题？** 在 [Discussions](https://github.com/QingShengmMa/SparkLaw/discussions) 中提问

**Questions?** Ask in [Discussions](https://github.com/QingShengmMa/SparkLaw/discussions)
