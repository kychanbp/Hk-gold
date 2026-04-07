from .base import GoldPrice, GoldPriceScraper
from .chowtaifook import ChowTaiFookScraper
from .chowsangsang import ChowSangSangScraper
from .lukfook import LukFookScraper
from .tsl import TSLScraper
from .laopu import LaoPuScraper

ALL_SCRAPERS = [
    ChowTaiFookScraper,
    ChowSangSangScraper,
    LukFookScraper,
    TSLScraper,
    LaoPuScraper,
]

__all__ = [
    "GoldPrice",
    "GoldPriceScraper",
    "ChowTaiFookScraper",
    "ChowSangSangScraper",
    "LukFookScraper",
    "TSLScraper",
    "LaoPuScraper",
    "ALL_SCRAPERS",
]
