from base64 import b64encode
from mkdocs.utils.meta import YAML_RE
from pydantic.error_wrappers import ValidationError
import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader

from mkdocs.exceptions import BuildError, PluginError

from jinja2 import Markup
from jinja2._compat import text_type

_js_escapes = {
    "\\": "\\u005C",
    "'": "\\u0027",
    '"': "\\u0022",
    ">": "\\u003E",
    "<": "\\u003C",
    "&": "\\u0026",
    "=": "\\u003D",
    "-": "\\u002D",
    ";": "\\u003B",
    "`": "\\u0060",
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}


def escapejs(s):
    if hasattr(s, "__html__"):
        return Markup(s.__html__())

    s = text_type(s)
    for key, value in _js_escapes.items():
        s = s.replace(key, value)
    return Markup(s)


def escapeb64(s):
    s = text_type(s)
    s = b64encode(s.encode()).decode()
    return Markup(s)


def read_source(self, config):
    try:
        with open(
            self.file.abs_src_path, "r", encoding="utf-8-sig", errors="strict"
        ) as f:
            source = f.read()
    except OSError:
        log.error(f"File not found: {self.file.src_path}")
        raise
    except ValueError:
        log.error(f"Encoding error reading file: {self.file.src_path}")
        raise

    m = YAML_RE.match(source)
    if m:
        try:
            data = yaml.load(m.group(1), SafeLoader)
            if not isinstance(data, dict):
                data = {}
        except Exception as exc:
            raise BuildError(f"Page's YAML metadata is malformed: {exc}")

        try:
            self.meta = config["meta_model_class"](**data)
        except ValidationError as exc:
            raise PluginError(
                f"Deserializing {self} page's meta failed with the following errors: {exc}"
            )

    self.markdown = source
    self.title = self.meta.title
