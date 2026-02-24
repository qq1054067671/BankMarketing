"""Model-facing @tool functions for web-research weather skill.

工具实现全部内聚在本文件，不依赖 helper.py。
"""

from __future__ import annotations

from typing import Dict

import requests
from langchain_core.tools import tool

CITY_ALIASES: Dict[str, str] = {
    "北京": "Beijing",
    "上海": "Shanghai",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "杭州": "Hangzhou",
    "成都": "Chengdu",
    "重庆": "Chongqing",
}

WEATHER_CODE_MAP: Dict[int, str] = {
    0: "晴朗",
    1: "大体晴朗",
    2: "局部多云",
    3: "阴天",
    45: "雾",
    48: "冻雾",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "浓毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "阵雨",
    81: "较强阵雨",
    82: "强阵雨",
    95: "雷暴",
}


def _normalize_city_name(city: str) -> str:
    return CITY_ALIASES.get(city.strip(), city.strip())


def _fetch_city_coordinates(city: str) -> dict:
    normalized_city = _normalize_city_name(city)
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": normalized_city, "count": 1, "language": "en", "format": "json"},
        timeout=15,
    )
    resp.raise_for_status()
    result = (resp.json().get("results") or [None])[0]
    if not result:
        raise ValueError(f"未找到城市：{city}（标准化后：{normalized_city}）")
    return {
        "city": result.get("name"),
        "country": result.get("country"),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
    }


def _fetch_current_weather(latitude: float, longitude: float) -> dict:
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        },
        timeout=15,
    )
    resp.raise_for_status()
    current = resp.json().get("current") or {}
    if not current:
        raise ValueError("天气服务暂时不可用，请稍后重试。")
    return current


def _interpret_weather_code(code: int) -> str:
    return WEATHER_CODE_MAP.get(code, f"未知天气代码({code})")


def build_tools():
    """Return model-callable @tool objects for this skill."""

    @tool
    def city_to_coordinates(city: str) -> str:
        """根据城市名查询经纬度。"""
        coord = _fetch_city_coordinates(city)
        return (
            f"city={coord['city']}, country={coord['country']}, "
            f"latitude={coord['latitude']}, longitude={coord['longitude']}"
        )

    @tool
    def weather_by_coordinates(latitude: float, longitude: float) -> str:
        """根据经纬度查询天气并解释天气代码。"""
        weather = _fetch_current_weather(latitude, longitude)
        weather_desc = _interpret_weather_code(int(weather.get("weather_code", -1)))
        return (
            f"temperature={weather.get('temperature_2m')}°C, "
            f"apparent_temperature={weather.get('apparent_temperature')}°C, "
            f"humidity={weather.get('relative_humidity_2m')}%, "
            f"wind_speed={weather.get('wind_speed_10m')}km/h, "
            f"weather={weather_desc}"
        )

    return [city_to_coordinates, weather_by_coordinates]
