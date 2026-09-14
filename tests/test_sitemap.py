from ssg.sitemap import build_sitemap


def test_every_url_is_listed_absolute():
    xml = build_sitemap(["/", "/writeup/"])
    assert "<loc>https://4n86rakam1.com/</loc>" in xml
    assert "<loc>https://4n86rakam1.com/writeup/</loc>" in xml


def test_characters_with_meaning_in_xml_are_escaped():
    # A raw & would make the sitemap unparseable without ElementTree.
    xml = build_sitemap(["/writeup/Tom_&_Jerry/"])
    assert "&amp;" in xml
    assert "_&_" not in xml


def test_the_default_namespace_carries_no_prefix():
    xml = build_sitemap(["/"])
    assert 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in xml
    assert "ns0:" not in xml


def test_no_lastmod_is_emitted():
    assert "lastmod" not in build_sitemap(["/"])
