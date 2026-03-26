"""Tests for scraper base class and price parsing."""

from matmoms.scrapers.ica import IcaScraper


class TestPriceParsing:
    """Test Swedish price format parsing."""

    def test_colon_format(self):
        assert IcaScraper._parse_price("23:90 kr") == 23.90

    def test_comma_format(self):
        assert IcaScraper._parse_price("23,90") == 23.90

    def test_integer_price(self):
        assert IcaScraper._parse_price("24 kr") == 24.0

    def test_price_with_prefix(self):
        assert IcaScraper._parse_price("Pris 23:90 kr") == 23.90

    def test_none_input(self):
        assert IcaScraper._parse_price(None) is None

    def test_empty_string(self):
        assert IcaScraper._parse_price("") is None

    def test_no_digits(self):
        assert IcaScraper._parse_price("kr") is None

    def test_unit_price_format(self):
        assert IcaScraper._parse_price("12:60 kr/kg") == 12.60

    def test_large_price(self):
        assert IcaScraper._parse_price("149:00") == 149.0
