from scrapers.portal_fetcher import is_antibot_content
from scrapers.portal_utils import extract_listing_urls, is_listing_detail_url


def test_fotocasa_detail_url_pattern():
    url = "https://www.fotocasa.es/es/comprar/vivienda/malaga-capital/centro/188536928/d"
    assert is_listing_detail_url(url)


def test_fotocasa_obra_nueva_detail_url():
    url = "https://www.fotocasa.es/es/comprar/vivienda/obra-nueva/estepona/20540697/186878035"
    assert is_listing_detail_url(url)


def test_fotocasa_index_is_not_detail():
    url = "https://www.fotocasa.es/es/comprar/viviendas/malaga-provincia/todas-las-zonas/l"
    assert not is_listing_detail_url(url)


def test_fotocasa_antibot_page_detected():
    md = "# SENTIMOS LA INTERRUPCIÓN\nEs posible que por alguna de estas razones no puedas seguir"
    assert is_antibot_content(markdown=md)


def test_extract_fotocasa_listing_urls():
    html = '''
    <a href="/es/comprar/vivienda/torrox/parking/188536928/d">Piso</a>
    <a href="https://www.fotocasa.es/es/comprar/vivienda/obra-nueva/estepona/20540697/186878035">Obra</a>
    '''
    urls = extract_listing_urls(
        html,
        page_url="https://www.fotocasa.es/es/comprar/viviendas/malaga-provincia/todas-las-zonas/l",
    )
    assert len(urls) == 2
