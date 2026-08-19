# -*- coding: utf-8 -*-
"""扫描服务：负责扫描生命周期（启动线程、进度上报、失败记录、报告生成）。"""
import logging
import threading

from ..errors import friendly_message

logger = logging.getLogger(__name__)


class ScanService:
    """扫描编排。通过 build_engine(progress_cb) 工厂创建引擎，解耦领域层。"""

    def __init__(self, build_engine, scan_repo, report_repo, reporter, top_n_provider=10):
        self.build_engine = build_engine
        self.scan_repo = scan_repo
        self.report_repo = report_repo
        self.reporter = reporter
        self.top_n_provider = top_n_provider  # int 或 callable() -> int
        self._lock = threading.RLock()
        self._engine = None
        self._state = {
            "running": False, "phase": "idle", "done": 0, "total": 0,
            "message": "", "run_id": None, "last_error": None,
        }

    # ------------------------------------------------------------------
    def start(self) -> bool:
        """启动一次扫描。已运行则返回 False（不重复启动）。"""
        with self._lock:
            if self._state["running"]:
                return False
            self._state.update(running=True, phase="start", done=0, total=1,
                               message="初始化…", run_id=None, last_error=None)

        def progress(phase, done, total, message):
            with self._lock:
                self._state.update(phase=phase, done=done, total=total, message=message)

        engine = self.build_engine(progress)
        self._engine = engine
        threading.Thread(target=self._run, args=(engine,), daemon=True).start()
        return True

    def get_progress(self) -> dict:
        with self._lock:
            return dict(self._state)

    def cancel(self) -> None:
        engine = self._engine
        if engine is not None:
            engine.cancel()

    # ------------------------------------------------------------------
    def _run(self, engine) -> None:
        try:
            result = engine.run()
            with self._lock:
                self._state.update(running=False, phase="done", done=1, total=1,
                                   message="扫描完成", run_id=result["run_id"])
            # 后台生成 LLM 报告，不阻塞主流程
            threading.Thread(target=self._generate_reports,
                             args=(result["run_id"],), daemon=True).start()
        except Exception as e:  # noqa: BLE001
            logger.exception("扫描失败")
            msg = friendly_message(e)
            with self._lock:
                self._state.update(running=False, phase="failed",
                                   message=f"扫描失败: {msg}", last_error=msg)

    def _generate_reports(self, run_id: int) -> None:
        try:
            top_n = self.top_n_provider() if callable(self.top_n_provider) else self.top_n_provider
            results = self.scan_repo.get_results(run_id)[:top_n]
            run = self.scan_repo.get_run(run_id) or {}
            market_text = self.reporter.generate_market_summary(run.get("summary") or {})
            for r in results:
                try:
                    if self.report_repo.get(run_id, r["ts_code"]):
                        continue
                    content = self.reporter.generate_report(r, market_text)
                    self.report_repo.save(run_id, r["ts_code"], content)
                except Exception as e:  # noqa: BLE001
                    logger.warning("个股报告生成失败 %s: %s", r.get("ts_code"), e)
        except Exception as e:  # noqa: BLE001
            logger.warning("报告生成阶段失败: %s", e)
