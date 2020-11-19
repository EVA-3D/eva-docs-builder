from mkdocs.plugins import BasePlugin


BADGE_CSS_CLASSES = {
    "OFFICIAL": "",
    "CONTRIB": "contrib",
    "DEPRECATED": "deprecated",
}


class EVAPlugin(BasePlugin):
    def on_page_markdown(self, markdown, page, config, files):
        for badge in page.meta.get("badges", []):
            badge_css_class = BADGE_CSS_CLASSES.get(badge.upper())
            if badge_css_class:
                markdown = f'<button class="badge md-button md-button-small md-button--primary {badge_css_class}">{badge}</button>\n\n{markdown}'
            else:
                markdown = f'<button class="badge md-button md-button-small md-button--primary">{badge}</button>\n\n{markdown}'
        return markdown
