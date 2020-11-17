from mkdocs.plugins import BasePlugin


class EVAPlugin(BasePlugin):
    def on_page_markdown(self, markdown, page, config, files):
        for badge in page.meta.get("badges", []):
            markdown = f'<button class="badge md-button md-button-small md-button--primary">{badge}</button>\n{markdown}'
        return markdown
