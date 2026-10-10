import time
from datetime import datetime

import httpx
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.message_components import Image, Node, Nodes, Plain
from astrbot.api.star import Context, Star

FURRY_IMG_API = "https://api.furry.ist/furry-img/?format=json"
FCC_RECENT_API = "https://api.furrycons.cn/open/event/recent"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

PAGE_SIZE = 5          # 每页展示条数
FETCH_PAGE_SIZE = 50   # 单次向 FCC 请求的条数
MAX_FETCH_PAGES = 20   # 分页拉取安全上限
CACHE_TTL = 1800       # 展会数据缓存时间（秒）


class FurryPlugin(Star):
    """Furry Image & Convention Info Plugin"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._convention_cache: dict = {"data": None, "ts": 0}
        self._cache_ttl = CACHE_TTL
        self._page_state: dict[str, int] = {}

    def _get_headers(self) -> dict:
        headers = dict(DEFAULT_HEADERS)
        # 新配置项为中文键，兼容旧键 fcc_api_token
        token = self.config.get("FCC 接口令牌", "") or self.config.get("fcc_api_token", "")
        if token:
            headers["Authorization"] = token
        return headers

    @filter.command("毛图")
    async def mao_command(self, event: AstrMessageEvent) -> None:
        """Send a random furry image"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(FURRY_IMG_API)
            if resp.status_code != 200:
                await event.send(MessageChain([Plain("API request failed")]))
                return
            data = resp.json()
            image_url = data.get("url", "")
            if image_url:
                await event.send(MessageChain([Image.fromURL(image_url)]))
            else:
                await event.send(MessageChain([Plain("No image URL found")]))

    @filter.command("兽聚")
    async def shouju_command(self, event: AstrMessageEvent) -> None:
        """Fetch upcoming furry conventions (page 1)"""
        chat_id = event.get_session_id()
        self._page_state[chat_id] = 0
        await self._send_page(event, 0)

    @filter.command("下一页")
    async def next_page_command(self, event: AstrMessageEvent) -> None:
        """Send next page of convention list"""
        chat_id = event.get_session_id()
        current = self._page_state.get(chat_id, 0)
        next_page = current + 1
        self._page_state[chat_id] = next_page
        await self._send_page(event, next_page)

    async def _send_page(self, event: AstrMessageEvent, page: int) -> None:
        try:
            events = await self._get_upcoming_events()
            if not events:
                await event.send(MessageChain([Plain("暂无近期展会信息")]))
                return

            total = len(events)
            start = page * PAGE_SIZE
            if start >= total:
                await event.send(MessageChain([Plain("已经是最后一页了")]))
                return

            end = min(start + PAGE_SIZE, total)
            page_events = events[start:end]

            self_id = event.get_self_id()

            nodes = []
            for ev in page_events:
                start_date = self._format_date(ev.get("startDate", ""))
                end_date = self._format_date(ev.get("endDate", ""))
                org = ev.get("organization", {}) or {}
                org_name = org.get("name", "")

                lines = [f"🐾 {ev.get('name', '')}"]
                if org_name:
                    lines.append(f"🏠 {org_name}")
                lines.append(f"📅 {start_date} ~ {end_date}")
                lines.append(f"📍 {ev.get('region', '')} · {ev.get('address', '')}")
                lines.append(f"📊 规模: {ev.get('scale', '未知')}")
                if ev.get("url"):
                    lines.append(f"🔗 {ev['url']}")

                # 封面图 -> 文字信息 -> 组织 logo
                content = []
                thumbnail = (ev.get("thumbnail") or "").strip()
                if thumbnail:
                    content.append(Image.fromURL(thumbnail))
                content.append(Plain("\n".join(lines)))
                logo = (org.get("logoUrl") or "").strip()
                if logo:
                    content.append(Image.fromURL(logo))

                nodes.append(Node(
                    content=content,
                    name="兽展日历",
                    uin=str(self_id),
                ))

            total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
            footer = f"第 {page + 1}/{total_pages} 页 (共 {total} 场展会)"
            if end < total:
                footer += "\n发送「下一页」查看更多"

            nodes.append(Node(
                content=[Plain(footer)],
                name="兽展日历",
                uin=str(self_id),
            ))

            await event.send(MessageChain([Nodes(nodes=nodes)]))
        except Exception as e:
            logger.error(f"Failed to fetch convention info: {e}")
            await event.send(MessageChain([Plain("获取展会信息失败，请稍后再试")]))

    async def _get_upcoming_events(self) -> list[dict]:
        now = time.time()
        if (
            self._convention_cache["data"]
            and now - self._convention_cache["ts"] < self._cache_ttl
        ):
            return self._convention_cache["data"]

        events: list[dict] = []
        seen: set = set()
        try:
            async with httpx.AsyncClient(timeout=30, headers=self._get_headers()) as client:
                current = 1
                while current <= MAX_FETCH_PAGES:
                    resp = await client.get(
                        FCC_RECENT_API,
                        params={
                            "keepOld": "true",
                            "current": current,
                            "pageSize": FETCH_PAGE_SIZE,
                        },
                    )
                    if resp.status_code != 200:
                        logger.warning(f"FCC API returned status {resp.status_code}")
                        break

                    payload = resp.json()
                    batch = payload.get("data") or []
                    if not batch:
                        break

                    added = 0
                    for ev in batch:
                        key = ev.get("id") or ev.get("slug") or ev.get("name")
                        if key and key in seen:
                            continue
                        if key:
                            seen.add(key)
                        events.append(ev)
                        added += 1

                    total = payload.get("total") or 0
                    effective = payload.get("pageSize") or FETCH_PAGE_SIZE
                    if total and len(events) >= total:
                        break
                    if added == 0:
                        break
                    if effective <= 0 or len(batch) < effective:
                        break
                    current += 1
        except Exception as e:
            logger.error(f"Failed to fetch convention info: {e}")

        events.sort(key=lambda x: x.get("startDate", ""))
        self._convention_cache["data"] = events
        self._convention_cache["ts"] = now
        return events

    @staticmethod
    def _format_date(iso_date: str) -> str:
        if not iso_date:
            return "待定"
        try:
            dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
            return dt.strftime("%Y.%m.%d")
        except Exception:
            return iso_date[:10]
