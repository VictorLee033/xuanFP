# -*- coding: utf-8 -*-
"""定时扫描与邮件推送服务。

- schedule(): 安排「下一个自然日」14:25 推送（一次性；是否交易日由用户自己判断）
- preview(): 立即手动触发一次（短线扫描 + 发邮件），后台线程执行
- 调度线程每 20 秒检查一次：
    * 已安排的 14:25 短线推送（窗口内触发；错过不补发）
    * 每个工作日 15:00~15:20 自动跑一次「标准模式」扫描并入回测库（周末跳过）
- 推送一律使用「短线模式」扫描（固定）
"""
import logging
import threading
import time
from datetime import datetime, date, timedelta

from .. import config as cfg
from .mailer import send_email

logger = logging.getLogger(__name__)

PUSH_TIME = "14:25"
WINDOW_MINUTES = 10
STD_TIME = "15:00"
STD_WINDOW = 20  # 15:00 ~ 15:20


def _pct(v):
    return "—" if v is None else f"{v:+.2f}%"


def _advice(s):
    if s is None:
        return "—"
    if s >= 85:
        return "建议加仓"
    if s >= 75:
        return "建议买入"
    if s >= 65:
        return "建议持有"
    if s >= 55:
        return "建议观望"
    return "建议回避"


class PushService:
    def __init__(self, push_repo, scan_repo, cache_repo, build_engine):
        self.push_repo = push_repo
        self.scan_repo = scan_repo
        self.cache_repo = cache_repo
        self.build_engine = build_engine
        self._previewing = False
        self._last_preview = None
        threading.Thread(target=self._loop, daemon=True).start()

    # ------------------------------------------------------------------
    def _mail_cfg(self):
        m = cfg.get_config().get("mail") or {}
        if m.get("sender") and m.get("auth_code") and m.get("recipient"):
            return m
        return None

    def schedule(self) -> dict:
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.push_repo.upsert(target_date=tomorrow, target_time=PUSH_TIME, status="pending")
        return {"ok": True, "target_date": tomorrow, "target_time": PUSH_TIME}

    def cancel(self) -> dict:
        self.push_repo.clear()
        return {"ok": True}

    def preview(self) -> dict:
        if self._previewing:
            return {"ok": False, "error": "预演已在运行中，请稍候"}
        self._previewing = True
        threading.Thread(target=self._run_push, args=("preview",), daemon=True).start()
        return {"ok": True, "running": True}

    def status(self) -> dict:
        job = self.push_repo.get() or {}
        return {
            "scheduled": job.get("status") == "pending",
            "target_date": job.get("target_date"),
            "target_time": job.get("target_time"),
            "job_status": job.get("status"),
            "last_send_at": job.get("last_send_at"),
            "last_error": job.get("last_error"),
            "preview_running": self._previewing,
            "last_preview": self._last_preview,
            "mail_configured": bool(self._mail_cfg()),
            "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    # ------------------------------------------------------------------
    def _loop(self):
        while True:
            try:
                self._check_fire()
                self._check_standard_scan()
            except Exception:  # noqa: BLE001
                logger.exception("推送调度检查异常")
            time.sleep(20)

    def _check_standard_scan(self):
        """每个工作日 15:00~15:20 自动跑一次标准模式扫描（记录到回测库+历史）。"""
        now = datetime.now()
        if now.weekday() >= 5:  # 周末跳过
            return
        hm = now.hour * 60 + now.minute
        if not (15 * 60 <= hm <= 15 * 60 + STD_WINDOW):
            return
        today = now.strftime("%Y-%m-%d")
        if self.cache_repo.get("std_scan:" + today):
            return
        self.cache_repo.set("std_scan:" + today, True, 86400)
        threading.Thread(target=self._run_standard_scan, daemon=True).start()

    def _run_standard_scan(self):
        try:
            engine = self.build_engine(lambda *a, **k: None, "normal")
            result = engine.run()
            logger.info("15:00 标准扫描完成并入库 run=%s pool=%s",
                        result.get("run_id"), result.get("pool_size"))
        except Exception:  # noqa: BLE001
            logger.exception("15:00 标准扫描失败")

    def _check_fire(self):
        job = self.push_repo.get()
        if not job or job.get("status") != "pending":
            return
        now = datetime.now()
        target_date = job.get("target_date") or ""
        target_time = job.get("target_time") or PUSH_TIME
        today = now.strftime("%Y-%m-%d")
        if today != target_date:
            if today > target_date:
                self.push_repo.mark_missed("目标日已过（可能未开机或服务未运行）")
            return
        hh, mm = (int(x) for x in target_time.split(":"))
        cur = now.hour * 60 + now.minute
        tgt = hh * 60 + mm
        if cur < tgt:
            return
        if cur > tgt + WINDOW_MINUTES:
            self.push_repo.mark_missed(f"错过 {target_time} 推送窗口（可能未开机或服务未运行）")
            return
        # 到点触发：先置 firing 防止重复触发
        self.push_repo.upsert(target_date=target_date, target_time=target_time, status="firing")
        threading.Thread(target=self._run_push, args=("scheduled",), daemon=True).start()

    # ------------------------------------------------------------------
    def _run_push(self, kind: str):
        ok, err = False, ""
        try:
            mail = self._mail_cfg()
            if not mail:
                raise RuntimeError("邮件未配置：请在「设置」里填写发件邮箱、SMTP授权码与收件邮箱")
            engine = self.build_engine(lambda *a, **k: None, "short")
            result = engine.run()
            rows = self.scan_repo.get_results(result["run_id"])[:10]
            html, subject = self._build_email(rows, result)
            send_email(mail["sender"], mail["auth_code"], mail["recipient"], subject, html,
                       mail.get("smtp_host", "smtp.qq.com"), int(mail.get("smtp_port", 465)))
            ok = True
        except Exception as e:  # noqa: BLE001
            err = str(e)
            logger.exception("邮件推送失败 kind=%s", kind)
            if kind == "scheduled":
                self.push_repo.mark_sent(False, err)
        finally:
            self._previewing = False
            if kind == "preview":
                self._last_preview = {"ok": ok, "error": err,
                                      "sent_at": time.time() if ok else None}
        if kind == "scheduled" and ok:
            self.push_repo.mark_sent(True)

    # ------------------------------------------------------------------
    def _build_email(self, rows, result):
        now = datetime.now()
        n = len(rows)
        subject = f"【xuanFP·短线】14:25 实时榜单 {now.strftime('%m-%d')} Top{n}"
        trs = []
        for i, r in enumerate(rows[:10]):
            price = r.get("price")
            atr = (r.get("factors") or {}).get("g15", {}).get("value")
            target = stop = "—"
            if price and atr:
                target = f"{price * (1 + 1.5 * atr / 100):.2f}"
                stop = f"{price * (1 - atr / 100):.2f}"
            trs.append(
                "<tr>"
                f"<td align='center'>{i + 1}</td>"
                f"<td>{r.get('ts_code', '')}</td>"
                f"<td><b>{r.get('name', '')}</b></td>"
                f"<td>{price if price is not None else '—'}</td>"
                f"<td>{_pct(r.get('pct_chg'))}</td>"
                f"<td align='center'><b>{r.get('score')}</b></td>"
                f"<td>{_advice(r.get('score'))}</td>"
                f"<td>{target}</td><td>{stop}</td>"
                f"<td style='font-size:12px;color:#555'>{self._highlight(r)}</td>"
                "</tr>"
            )
        html = (
            "<html><body style='font-family:Microsoft YaHei,Arial,sans-serif'>"
            f"<h2 style='color:#d35400'>⚡ xuanFP 短线模式 · {now.strftime('%Y-%m-%d %H:%M')} 实时榜单</h2>"
            f"<p>覆盖全市场 <b>{result.get('universe_size', '-')}</b> 只，入围评分池 <b>{result.get('pool_size', '-')}</b> 只。"
            "短线权重以趋势/量价/资金/情绪为主；次日止盈=现价×1.015×ATR，止损=现价−1.0×ATR。</p>"
            "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;font-size:13px'>"
            "<tr style='background:#f0f0f0'><th>#</th><th>代码</th><th>名称</th><th>现价</th><th>涨跌幅</th>"
            "<th>得分</th><th>建议</th><th>次日止盈</th><th>次日止损</th><th>核心亮点</th></tr>"
            + "".join(trs) +
            "</table>"
            "<p style='color:#999;font-size:11px'>本邮件由 xuanFP 自动生成，仅供参考，不构成投资建议。买入前请自行判断。</p>"
            "</body></html>"
        )
        return html, subject

    def _highlight(self, r):
        # 短线邮件：优先展示短线相关维度（趋势/量价/资金/情绪），不足再补其他维度
        short_dims = ("trend", "momentum", "capital", "chip")
        dims = r.get("dimensions") or {}
        scored = [(v.get("score") or 0, v.get("name"), k)
                  for k, v in dims.items() if v.get("score") is not None]
        scored.sort(reverse=True)
        short = [x for x in scored if x[2] in short_dims and x[0] >= 60]
        rest = [x for x in scored if x[2] not in short_dims]
        pick = (short + rest)[:2]
        parts = [f"{n}（{s:.0f}分）" for s, n, _k in pick]
        # 因子部分：只取短线相关维度的因子名
        fs = r.get("factors") or {}
        topf = sorted([(v.get("score") or 0, v.get("name"), v.get("dim"))
                       for v in fs.values() if v.get("score") is not None], reverse=True)
        fn = "、".join([n for s, n, d in topf if d in short_dims and s >= 60][:2])
        hl = "、".join(parts)
        if fn:
            hl += "；" + fn + " 领先"
        return hl
