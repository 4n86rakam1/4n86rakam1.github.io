"""Sitemap generation, built through ElementTree so that a URL carrying
characters with meaning in XML cannot break the document."""

from xml.etree import ElementTree

from .config import SITE_URL

SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def build_sitemap(urls):
    """Return the sitemap document for the given site-relative URLs.

    No `lastmod`: clone and rsync rewrite source mtimes and the writeups carry
    no date of their own, so the field would be wrong or blog-only.
    """
    # Registering the namespace as the default keeps ns0: off every element.
    ElementTree.register_namespace("", SITEMAP_NAMESPACE)
    root = ElementTree.Element(f"{{{SITEMAP_NAMESPACE}}}urlset")
    for url in urls:
        entry = ElementTree.SubElement(root, f"{{{SITEMAP_NAMESPACE}}}url")
        location = ElementTree.SubElement(entry, f"{{{SITEMAP_NAMESPACE}}}loc")
        location.text = SITE_URL + url
    return ElementTree.tostring(root, encoding="unicode", xml_declaration=True)
