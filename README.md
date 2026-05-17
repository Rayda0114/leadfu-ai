# 領富 AI · LeadFu AI

> AI 台股研究助理・上市/上櫃/興櫃 2,310 檔資料整理

[![Deploy on Netlify](https://img.shields.io/badge/Netlify-Live-00C7B7?logo=netlify)](https://leadfuai.com)
[![Data Source](https://img.shields.io/badge/Data-TPEx%20OpenAPI-1B4332)](https://www.tpex.org.tw/openapi/)

## 線上版

**https://leadfuai.com**

## 內容

- 即時興櫃股票報價（TPEx 官方資料，每日更新）
- 887 家興櫃公司基本資料 + 月營收
- AI 智能分析（預留 Claude API 接口）
- 每日 K 線累積、新聞、重大訊息
- 老錢風格設計，鎖定 45-75 歲投資人

## 技術棧

- 純靜態 HTML / CSS / JavaScript（無前端框架）
- Python 3 stdlib 爬蟲腳本（無外部依賴）
- GitHub Actions 每日自動更新
- Netlify 自動部署
- 資料源：TPEx 櫃買中心 OpenAPI + Google News RSS

## 自動化流程

```
GitHub Actions (每日 15:00 台北)
  → python scripts/run_all.py
  → 抓 6 個資料源寫進 data/*.json
  → git push
  → Netlify 偵測到 push
  → 自動重新部署
```

## 本地開發

```bash
# 抓最新資料
python scripts/run_all.py

# 啟動本機伺服器測試
python -m http.server 8080
# 開 http://localhost:8080
```

## 部署文件

詳見 [DEPLOY.md](DEPLOY.md)

## LINE 官方帳號

[@041exgtv](https://line.me/R/ti/p/@041exgtv) ・ 每日 AI 台股盤後資料整理摘要

---

© 2026 領富 AI · 投資前請審慎評估風險
