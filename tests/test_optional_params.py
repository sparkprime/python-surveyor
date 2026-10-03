"""Tests for the ``optional-param-default`` check."""

from python_surveyor.checks.optional_params import run


def test_defaulted_positional_param(make_source_file, empty_corpus):
    source = "def f(a=1):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "optional-param-default"


def test_mixed_defaulted_positional(make_source_file, empty_corpus):
    source = "def f(a, b=2):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_defaulted_kwonly(make_source_file, empty_corpus):
    source = "def f(*, a=1):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_no_defaults_not_flagged(make_source_file, empty_corpus):
    source = "def f(a, b):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_args_kwargs_not_flagged(make_source_file, empty_corpus):
    source = "def f(*args, **kwargs):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_defaulted_param_names_in_notes(make_source_file, empty_corpus):
    source = "def f(a, b=2, *, c=3):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    notes = "\n".join(findings[0].notes)
    assert "b" in notes
    assert "c" in notes
    # "a" should not appear in the defaulted-params note (it has no default)
    defaulted_note = [n for n in findings[0].notes if "Defaulted params" in n][0]
    assert "a" not in defaulted_note.split(":")[-1]


def test_signature_excerpt_not_full_body(make_source_file, empty_corpus):
    source = "def f(a=1):\n" + "    x = 1\n" * 30 + "    return x\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpt = findings[0].excerpts[0]
    assert excerpt.start_line == 1
    assert excerpt.end_line == 1


def test_signature_elides_non_defaulted_params(make_source_file, empty_corpus):
    source = "def f(a, b, c=3):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpt = findings[0].excerpts[0]
    assert excerpt.start_line == 1
    assert excerpt.end_line == 1


def test_signature_elides_with_multiline_def(make_source_file, empty_corpus):
    source = "def f(\n    a,\n    b,\n    c=3,\n):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpt = findings[0].excerpts[0]
    assert excerpt.start_line == 4
    assert excerpt.end_line == 5


# --- FastAPI / Flask route-handler exclusion ------------------------------


def test_fastapi_app_get_handler_excluded(make_source_file, empty_corpus):
    source = (
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/x')\n"
        "def handler(q: str = 'a'):\n"
        "    return q\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_fastapi_router_post_handler_excluded(make_source_file, empty_corpus):
    source = (
        "from fastapi import APIRouter as AR\n"
        "router = AR()\n"
        "@router.post('/x')\n"
        "async def create(q: int = 0):\n"
        "    return q\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_fastapi_module_import_form_excluded(make_source_file, empty_corpus):
    source = (
        "import fastapi\n"
        "app = fastapi.FastAPI()\n"
        "@app.get('/x')\n"
        "def handler(q: str = 'a'):\n"
        "    return q\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_fastapi_api_route_handler_excluded(make_source_file, empty_corpus):
    source = (
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.api_route('/x', methods=['GET'])\n"
        "def handler(q: str = 'a'):\n"
        "    return q\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_fastapi_websocket_handler_excluded(make_source_file, empty_corpus):
    source = (
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.websocket('/ws')\n"
        "async def ws_handler(q: str = 'a'):\n"
        "    pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_flask_app_route_handler_excluded(make_source_file, empty_corpus):
    source = (
        "from flask import Flask\n"
        "app = Flask(__name__)\n"
        "@app.route('/x')\n"
        "def handler(q='a'):\n"
        "    return q\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_flask_blueprint_get_handler_excluded(make_source_file, empty_corpus):
    source = (
        "from flask import Blueprint\n"
        "bp = Blueprint('bp', __name__)\n"
        "@bp.get('/x')\n"
        "def handler(q='a'):\n"
        "    return q\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_fastapi_handler_and_plain_function_mixed(make_source_file, empty_corpus):
    """A route handler is excluded but a plain defaulted function still flagged."""
    source = (
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/x')\n"
        "def handler(q: str = 'a'):\n"
        "    return q\n"
        "def plain(x=1):\n"
        "    return x\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].line == 6


def test_non_framework_decorator_still_flagged(make_source_file, empty_corpus):
    """A custom .get() decorator with no fastapi/flask import is still flagged."""
    source = (
        "class MyAPI:\n"
        "    def get(self, *a, **k):\n"
        "        def deco(f):\n"
        "            return f\n"
        "        return deco\n"
        "api = MyAPI()\n"
        "@api.get()\n"
        "def handler(q=1):\n"
        "    return q\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_no_framework_import_still_flagged(make_source_file, empty_corpus):
    """Decorator shaped like a route but with no fastapi/flask import is flagged."""
    source = (
        "app = object()\n" "@app.get('/x')\n" "def handler(q=1):\n" "    return q\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_staticmethod_decorator_still_flagged(make_source_file, empty_corpus):
    """Unrelated decorators (staticmethod) don't cause exclusion."""
    source = "class C:\n" "    @staticmethod\n" "    def f(a=1):\n" "        return a\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
