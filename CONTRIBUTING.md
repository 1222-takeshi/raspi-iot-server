# Contributing Guide

## 開発フロー

1. **Issue を作成** — 作業前に必ず Issue を作成し、背景・目的・完了条件を記載する
2. **ブランチを切る** — `feat/<機能名>` または `fix/<修正内容>` の命名規則で作業ブランチを作成
3. **スモール PR** — 1 PR = 1 つの論理的変更に留める（レビューしやすいサイズに保つ）
4. **PR を出す** — PR タイトルは英語、本文は日本語。`Closes #<issue番号>` でリンクする

## コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/) に従う。

```
<type>(<scope>): <summary>

[optional body]

[optional footer]
```

### type 一覧

| type       | 用途                                         |
|------------|----------------------------------------------|
| `feat`     | 新機能の追加                                  |
| `fix`      | バグ修正                                      |
| `chore`    | ビルド・設定・依存関係など本質的でない変更     |
| `docs`     | ドキュメントのみの変更                        |
| `refactor` | 動作を変えないコードの整理・改善              |
| `test`     | テストの追加・修正                            |
| `style`    | フォーマット、セミコロン等（ロジック変更なし）|
| `perf`     | パフォーマンス改善                            |
| `ci`       | CI/CD 設定の変更                              |

### scope 例（任意）

`server`, `serial`, `dashboard`, `deploy`, `db`

### 例

```
feat(serial): auto-detect ESP32 USB port
fix(db): handle null humidity in sensor reading
chore(deploy): add systemd service template
docs: update ESP32 serial format in README
```

## ブランチ命名

```
feat/<機能名>       # 例: feat/serial-reader
fix/<修正内容>      # 例: fix/serial-reconnect
chore/<内容>        # 例: chore/setup-ci
```

## PR テンプレート

`.github/pull_request_template.md` が自動適用される。
