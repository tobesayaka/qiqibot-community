#!/usr/bin/env bash
set -euo pipefail

##############################################################################
# 配置区，请修改这几个变量为你自己的真实值
##############################################################################
# 私有仓库的稳定发布分支
PRIVATE_STABLE_BRANCH="main"

# 导出快照的临时工作目录（相对于私有仓库的上级目录）
OPEN_WORKSPACE="../qiqibot-community"

# 开源仓库 git 地址（public github）
OPEN_REPO_URL="https://github.com/tobesayaka/qiqibot-community.git"

# 【重要】开源仓库独有的文件/目录，同步时不要被私有仓库覆盖！
# 例如 LICENSE、公开README、公开文档目录，多个用空格隔开
OPEN_ONLY_FILES="LICENSE README.md docs"

# -------------------------- 新增：需要过滤/删除的文件、目录黑名单 --------------------------
# 支持目录、文件，相对仓库根路径；多个空格隔开
# 示例： "internal .env.dev .env.prod config/secrets.json scripts/private"
EXCLUDE_PATHS=".env.dev .env.prod docs protos scripts AGENTS.md qiqibot.md README.md"
##############################################################################

echo "=== 1. 切换到私有仓库稳定分支 ${PRIVATE_STABLE_BRANCH} ==="
git checkout "${PRIVATE_STABLE_BRANCH}"
git pull origin "${PRIVATE_STABLE_BRANCH}"

# 保存开源独有文件（先备份，后面恢复）
mkdir -p "${OPEN_WORKSPACE}"
BACKUP_DIR=$(mktemp -d)
echo "备份开源独有文件到临时目录: ${BACKUP_DIR}"
for f in ${OPEN_ONLY_FILES}; do
    if [ -e "${OPEN_WORKSPACE}/${f}" ]; then
        cp -r "${OPEN_WORKSPACE}/${f}" "${BACKUP_DIR}/"
    fi
done

echo "=== 2. git archive 导出稳定版本文件快照 ==="
rm -rf "${OPEN_WORKSPACE:?}"/*
git archive HEAD | tar -x -C "${OPEN_WORKSPACE}"

# ====================== 新增：黑名单过滤删除 ======================
echo "=== 2.1 删除黑名单文件/目录：${EXCLUDE_PATHS} ==="
for p in ${EXCLUDE_PATHS}; do
    target="${OPEN_WORKSPACE}/${p}"
    if compgen -G "${target}" > /dev/null; then
        rm -rf "${target}"
        echo "  removed: ${p}"
    fi
done

echo "=== 3. 恢复开源仓库独有文件（不被私有代码覆盖） ==="
for f in ${OPEN_ONLY_FILES}; do
    if [ -e "${BACKUP_DIR}/${f}" ]; then
        cp -r "${BACKUP_DIR}/${f}" "${OPEN_WORKSPACE}/"
    fi
done
rm -rf "${BACKUP_DIR}"

echo "=== 4. 进入开源工作目录，git操作 ==="
cd "${OPEN_WORKSPACE}"

# 原来你写的删除 .env.dev .env.prod，已经可以迁移到 EXCLUDE_PATHS，这里保留也没关系
rm -f .env.dev .env.prod

# 如果还没有初始化，则初始化+设置remote；已有则跳过
if [ ! -d ".git" ]; then
    git init
    git remote add origin "${OPEN_REPO_URL}"
fi

git add .
# 自动检测是否有变更
if git diff --cached --quiet; then
    echo "✅ 没有检测到代码变更，无需提交推送，退出"
    exit 0
fi

# 提交信息，可以自定义
COMMIT_MSG="feat: sync open source release $(date +'%Y-%m-%d %H:%M')"
git commit -m "${COMMIT_MSG}"

echo "=== 5. 推送到开源仓库 main 分支 ==="
git push -u origin main

echo "🎉 同步完成！开源仓库已更新"