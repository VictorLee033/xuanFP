# -*- coding: utf-8 -*-
"""组合根（Composition Root）：装配所有分层依赖。

这是唯一知道所有具体实现的模块——各层只依赖接口/抽象，
由这里把具体的数据源、仓库、服务组装起来并注入。
"""
import logging

from . import config as cfg
from .datasources import EastMoneyClient, TencentClient
from .datasources.fundamentals import FundamentalsClient
from .domain.scanner.engine import ScanEngine
from .llm import reporter
from .repositories import (Database, CacheRepository, ScanRepository,
                           ReportRepository, Top10Repository, PushRepository)
from .services import (BacktestService, HistoryService, MarketService,
                       PushService, ScanService)

logger = logging.getLogger(__name__)


class Container:
    """应用依赖容器：持有数据源、仓库与服务实例。"""

    def __init__(self):
        self.db = Database(cfg.CACHE_DB)
        self.cache_repo = CacheRepository(self.db)
        self.scan_repo = ScanRepository(self.db)
        self.report_repo = ReportRepository(self.db)
        self.top5_repo = Top10Repository(self.db)
        self.push_repo = PushRepository(self.db)

        # 外部数据源（轻量、按需重读配置）
        self.em = EastMoneyClient()
        self.tx = TencentClient()
        self.fund = FundamentalsClient()

        # 应用服务
        self.market = MarketService(self.em, self.tx, self.scan_repo, self.report_repo)
        self.history = HistoryService(self.scan_repo)
        self.backtest = BacktestService(self.top5_repo, self.tx)
        self.scan = ScanService(
            build_engine=self._build_engine,
            scan_repo=self.scan_repo,
            report_repo=self.report_repo,
            reporter=reporter,
            top_n_provider=lambda: cfg.get_config()["llm"].get("top_n_reports", 10),
        )
        self.push = PushService(
            push_repo=self.push_repo,
            scan_repo=self.scan_repo,
            cache_repo=self.cache_repo,
            build_engine=self._build_engine,
        )

    def _build_engine(self, progress, mode: str = "normal") -> ScanEngine:
        c = cfg.get_config()
        sc = dict(c["scanner"])
        sc["mode"] = mode
        weights = c["scanner"]["weights"]
        if mode and mode != "normal":
            preset = (c.get("presets") or {}).get(mode) or {}
            if preset.get("weights"):
                weights = preset["weights"]
            if preset.get("pe_max"):
                sc["pe_max"] = preset["pe_max"]
        return ScanEngine(
            em=self.em, tx=self.tx, fund=self.fund,
            cache_repo=self.cache_repo, scan_repo=self.scan_repo,
            weights=weights, scanner_cfg=sc,
            progress=progress, top5_repo=self.top5_repo,
        )

    def reload_datasources(self) -> None:
        """配置更新后，失效数据源缓存，使新配置即时生效。"""
        self.em.invalidate()
        self.tx.invalidate()
        logger.info("数据源配置已重载")

    def close(self) -> None:
        try:
            self.db.close()
        except Exception:  # noqa: BLE001
            pass


_container: Container | None = None


def build_container() -> Container:
    """构建（或复用）全局依赖容器。"""
    global _container
    if _container is None:
        _container = Container()
    return _container
