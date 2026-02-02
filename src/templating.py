from fastapi.templating import Jinja2Templates
from markupsafe import Markup

templates = Jinja2Templates(directory="src/templates")

_original_template_response = templates.TemplateResponse


def _template_response_with_content(name, context, **kwargs):
    request = context.get("request")
    content_dict = getattr(request.state, "site_content", {}) if request else {}

    def t(key: str, default: str = "") -> Markup:
        value = content_dict.get(key)
        return Markup(value) if value else Markup(default)

    context.setdefault("t", t)

    # Inject shop settings so base.html header/footer always has access
    if request:
        shop_settings = getattr(request.state, "shop_settings", None)
        context.setdefault("settings", shop_settings)
        context.setdefault("shop_settings", shop_settings)

    return _original_template_response(name, context, **kwargs)


templates.TemplateResponse = _template_response_with_content
