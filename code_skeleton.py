"""Tree-sitter PHP skeletons of reference files for the coding prompt (NESTI_TREE_SITTER_ENABLED)."""
import functools
import logging
import os
import re

logger = logging.getLogger(__name__)

_GRAMMAR = "php"
# Bodies the coder needs verbatim: validation, serialisation, casts, factory states, test setup.
_KEPT_METHODS = frozenset({"rules", "messages", "attributes", "toArray", "casts", "definition", "setUp"})
_MAX_KEPT_BODY_LINES = 5  # relationship/scope one-liners stay whole
_ELIDED = "{ … }"
_FUNCTIONS = frozenset({"method_declaration", "function_definition"})


def enabled() -> bool:
    """NESTI_TREE_SITTER_ENABLED, default off; read on every call."""
    return os.environ.get("NESTI_TREE_SITTER_ENABLED", "").strip().lower() in {"true", "1", "yes", "on"}


@functools.cache
def _parser():
    """PHP parser from the baked grammar, or None. Never triggers a run-time download."""
    try:
        import tree_sitter_language_pack as pack

        if _GRAMMAR not in pack.downloaded_languages():
            logger.warning("Code skeletons unavailable: the %s grammar is not in %s.", _GRAMMAR, pack.cache_dir())
            return None
        return pack.get_parser(_GRAMMAR)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Code skeletons unavailable: %s", exc)
        return None


def php_skeleton(source: str, keep_first: re.Pattern | None = None) -> str | None:
    """*source* with long function/method bodies replaced by `{ … }`; None when not shorter or not parseable.

    Bodies of at most five lines, the methods in ``_KEPT_METHODS`` and the first
    body *keep_first* matches stay verbatim. Never raises.
    """
    try:
        parser = _parser()
        if parser is None:
            return None
        data = source.encode("utf-8")
        tree = parser.parse(data)
        if tree.root_node.has_error:
            return None
        cuts: list[tuple[int, int]] = []
        kept_first = keep_first is None
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            body = node.child_by_field_name("body") if node.type in _FUNCTIONS else None
            if body is not None and body.type == "compound_statement":
                name_node = node.child_by_field_name("name")
                name = data[name_node.start_byte:name_node.end_byte].decode("utf-8") if name_node else ""
                lines = body.end_point[0] - body.start_point[0] + 1
                if lines <= _MAX_KEPT_BODY_LINES or name in _KEPT_METHODS:
                    stack.extend(reversed(node.children))
                    continue
                if not kept_first and keep_first.search(data[body.start_byte:body.end_byte].decode("utf-8")):
                    kept_first = True
                    stack.extend(reversed(node.children))
                    continue
                cuts.append((body.start_byte, body.end_byte))
                continue
            stack.extend(reversed(node.children))
        for start, end in sorted(cuts, reverse=True):
            data = data[:start] + _ELIDED.encode("utf-8") + data[end:]
        result = data.decode("utf-8")
        return result if len(result) < len(source) else None
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("PHP skeleton failed: %s", exc)
        return None
