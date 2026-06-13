# fcitx5 アドオンの upstream (fcitx/mozc) 更新手順

このドキュメントは、fcitx/mozc の `src/unix/fcitx5/` ディレクトリおよび `scripts/` ディレクトリに更新があった場合の取り込み手順を説明します。

## 前提条件

- `fcitx-mozc` リモートが登録済みであること
- `src/unix/fcitx5/` および `scripts/` が git subtree で管理されていること

## リモートの確認・追加

```bash
# リモート確認
git remote -v

# 未登録の場合
git remote add fcitx-mozc https://github.com/fcitx/mozc.git
```

## 更新手順 (git subtree pull)

### 方法 1: 推奨 (squash merge)

```bash
# 1. upstream から最新を取得
git fetch fcitx-mozc

# 2. ディレクトリのみを取り込み (squash してコミット履歴をきれいに)

# src/unix/fcitx5 の場合:
git subtree pull --prefix=src/unix/fcitx5 fcitx-mozc fcitx --squash -m "Update fcitx5 from fcitx/mozc"

# scripts の場合:
git subtree pull --prefix=scripts fcitx-mozc fcitx --squash -m "Update scripts from fcitx/mozc"
```

### 方法 2: 通常の merge (履歴を保持)

```bash
git fetch fcitx-mozc

# src/unix/fcitx5 の場合:
git subtree pull --prefix=src/unix/fcitx5 fcitx-mozc fcitx -m "Merge fcitx5 from fcitx/mozc"

# scripts の場合:
git subtree pull --prefix=scripts fcitx-mozc fcitx -m "Merge scripts from fcitx/mozc"
```

## 更新後の確認

```bash
# 変更内容確認
git diff HEAD~1 -- src/unix/fcitx5/
git diff HEAD~1 -- scripts/

# ビルドテスト
cd src
bazelisk build //unix/fcitx5:fcitx5-mozc.so --config release_build --config oss_linux
```

## トラブルシューティング

### コンフリクトが発生した場合

```bash
# コンフリクト解決後
git add src/unix/fcitx5/
# または git add scripts/
git commit -m "Resolve conflicts from fcitx/mozc update"
```

### 履歴が壊れた場合 (再適用)

```bash
# 現在のディレクトリを削除して再適用

# src/unix/fcitx5 の場合:
rm -rf src/unix/fcitx5
git subtree add --prefix=src/unix/fcitx5 fcitx-mozc fcitx --squash -m "Re-add fcitx5 from fcitx/mozc"

# scripts の場合:
rm -rf scripts
git subtree add --prefix=scripts fcitx-mozc fcitx --squash -m "Re-add scripts from fcitx/mozc"
```

## 定期的な更新の自動化 (GitHub Actions 例)

`.github/workflows/update-fcitx5.yml`:

```yaml
name: Update fcitx5 from upstream

on:
  schedule:
    - cron: '0 0 * * 0'  # 毎週日曜
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - name: Add fcitx-mozc remote
        run: git remote add fcitx-mozc https://github.com/fcitx/mozc.git
      - name: Fetch and pull fcitx5 & scripts
        run: |
          git fetch fcitx-mozc
          git subtree pull --prefix=src/unix/fcitx5 fcitx-mozc fcitx --squash -m "Update fcitx5 from fcitx/mozc [auto]"
          git subtree pull --prefix=scripts fcitx-mozc fcitx --squash -m "Update scripts from fcitx/mozc [auto]"
      - name: Push changes
        run: git push
```

## 注意事項

1. **mozkey 固有の変更を加えている場合**、subtree pull で上書きされる可能性があります。その場合は手動でマージしてください。

2. **BUILD.bazel の互換性**: fcitx/mozc の BUILD.bazel が mozkey の `//:build_defs.bzl` と互換性があることを確認してください。

3. **依存関係の変更**: fcitx/mozc 側で新しい依存が追加された場合、`src/MODULE.bazel` の更新が必要になることがあります。

## 関連コマンド一覧

| コマンド | 用途 |
|----------|------|
| `git subtree pull --prefix=src/unix/fcitx5 fcitx-mozc fcitx --squash` | fcitx5 更新取り込み (推奨) |
| `git subtree pull --prefix=scripts fcitx-mozc fcitx --squash` | scripts 更新取り込み (推奨) |
| `git subtree push --prefix=src/unix/fcitx5 fcitx-mozc fcitx` | 変更を upstream に送る (稀) |
| `git subtree push --prefix=scripts fcitx-mozc fcitx` | 変更を upstream に送る (稀) |
| `git log --oneline -- src/unix/fcitx5` | 取り込み履歴確認 |
| `git log --oneline -- scripts` | 取り込み履歴確認 |