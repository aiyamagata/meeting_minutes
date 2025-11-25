# 実行方法ガイド

## 📍 プロジェクトルートとは？

プロジェクトルート = プロジェクトの一番上のフォルダ

```
meeting_minutes for everyone/  ← これがプロジェクトルート
├── README.md
├── config/
├── python/
│   └── main.py
└── ...
```

## ✅ 正しい実行方法

### 1. プロジェクトルートに移動

```bash
cd "/Users/yamagataai/meeting_minutes for everyone"
```

### 2. 実行

```bash
python python/main.py --test
```

**ポイント**: `python/` を付けて実行する

---

## ❌ 間違った実行方法

### 間違い1: pythonディレクトリに入ってから実行

```bash
cd python          # ← これが間違い
python main.py --test
```

**問題**: 設定ファイルの相対パスが間違う

### 間違い2: python/main.py を直接実行

```bash
python main.py --test  # ← プロジェクトルートにいないと動かない
```

---

## 🔍 現在のディレクトリを確認する方法

```bash
pwd
```

プロジェクトルートにいる場合：
```
/Users/yamagataai/meeting_minutes for everyone
```

`python` ディレクトリにいる場合：
```
/Users/yamagataai/meeting_minutes for everyone/python
```

---

## 📝 簡単な覚え方

**「プロジェクトルートから、`python/` を付けて実行する」**

```bash
# プロジェクトルートにいることを確認
pwd

# 実行
python python/main.py --test
```

