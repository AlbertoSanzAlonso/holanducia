from scrapers.image_utils import is_portal_index_url
from scrapers.portal_utils import extract_listing_urls, is_listing_detail_url


def test_habitaclia_detail_url_pattern():
    url = "https://www.habitaclia.com/comprar-piso-covadonga-sabadell-i55621000000139.htm"
    assert is_listing_detail_url(url)
    assert not is_portal_index_url(url)


def test_habitaclia_index_url_pattern():
    url = "https://www.habitaclia.com/viviendas-malaga.htm"
    assert is_portal_index_url(url)
    assert not is_listing_detail_url(url)


def test_habitaclia_legacy_listado_is_index_not_detail():
    url = "https://www.habitaclia.com/comprar-vivienda-en-malaga/listado.htm"
    assert is_portal_index_url(url)
    assert not is_listing_detail_url(url)


def test_migrate_legacy_habitaclia_listado_url():
    old = "https://www.habitaclia.com/comprar-vivienda-en-malaga/listado.htm"
    new = "https://www.habitaclia.com/viviendas-malaga.htm"
    from scrapers.portal_utils import normalize_habitaclia_index_url, normalize_portal_urls

    assert normalize_habitaclia_index_url(old) == new
    assert normalize_portal_urls([old]) == [new]


def test_extract_habitaclia_listing_urls_from_markdown():
    md = """
    [Piso en Málaga](https://www.habitaclia.com/comprar-piso-malaga-centro-i12345678901234.htm)
    """
    urls = extract_listing_urls(
        markdown=md,
        page_url="https://www.habitaclia.com/viviendas-malaga.htm",
    )
    assert len(urls) == 1
    assert urls[0].endswith("-i12345678901234.htm")
