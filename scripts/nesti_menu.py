#!/usr/bin/env python3
"""Argument-less host ``nesti`` TTY menu, run only by the checkout's .venv Python.

Requires Python 3.9+ and requirements-host.txt. Actions re-run scripts/nesti;
provider/model browsing reads credential-free container JSON; selecting an
inference model requires confirmation. Plugin secrets use stdin, never argv.
"""
from __future__ import annotations

import logging
import os
import json
import subprocess
import sys

import nesti_plugins

logger = logging.getLogger(__name__)
ROOT = nesti_plugins.default_root()
LAUNCHER = os.path.join(ROOT, "scripts", "nesti")
CONTAINER = "nesti-orchestrator"
NOT_RUNNING = "nesti-orchestrator is not running (start it with: docker compose up -d)"


def _run(args: list[str], stdin_text: str | None = None) -> int:
    try:
        return subprocess.run(["sh", LAUNCHER, *args], input=stdin_text, text=True).returncode
    except KeyboardInterrupt:
        return 130


def _orchestrator_running() -> bool:
    try:
        result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER],
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _metadata(args: list[str]) -> list[dict] | None:
    result = subprocess.run(["docker", "exec", CONTAINER, "nesti", *args, "--json"],
                            capture_output=True, text=True)
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return None
    try:
        data = json.loads(result.stdout)
        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise ValueError("Expected metadata rows")
        return data
    except ValueError:
        print("Cannot read provider metadata; update the orchestrator CLI.", file=sys.stderr)
        return None


def _consumers() -> list[tuple[str, bool]] | None:
    providers = _metadata(["/provider"])
    if providers is None:
        return None
    return [(p["name"], p.get("authenticated") is True) for p in providers
            if p.get("kind") == "consumer" and isinstance(p.get("name"), str)]


def _model_title(model: dict) -> str:
    context = f"{model['context']:,}" if model["context"] is not None else "unknown"
    return (f"{model['id']} — {model['name']} | context {context} | "
            f"in ${model['input_price']} / out ${model['output_price']} per 1M")


def _models_menu(q, name: str) -> None:
    models = _metadata(["/provider", "models", name])
    if models is None:
        return
    query = ""
    while True:
        matches = [m for m in models if query.casefold() in f"{m['id']} {m['name']}".casefold()]
        choices = [q.Choice("Filter models by ID/name" + (f" ({query})" if query else ""), value="filter")]
        for model in matches:
            title = _model_title(model)
            if model["free"]:
                title = ([("bold fg:ansigreen", "[FREE] "), ("", title)]
                         if sys.stdout.isatty() and "NO_COLOR" not in os.environ else "[FREE] " + title)
            choices.append(q.Choice(title, value=model))
        if not matches:
            choices.append(q.Choice("No matching text models.", disabled="Change the filter"))
        choices.append(q.Choice("Back", value="back"))
        selected = _ask(q.select(f"{name} models", choices=choices))
        if selected is None or selected == "back":
            return
        if selected == "filter":
            value = _ask(q.text("Filter by model ID or name (empty shows all)", default=query))
            if value is not None:
                query = value.strip()
        else:
            print(("[FREE] " if selected["free"] else "") + _model_title(selected))
            print("Catalog prices are indicative; routed provider pricing may differ.")
            print("Selecting a model affects subsequent OpenRouter calls; API enable flags and consumer priority stay unchanged.")
            action = _ask(q.select("Model details", choices=["Use this model for Nesti", "Back"]))
            if action is None:
                return
            if action == "Use this model for Nesti" and _ask(q.confirm(
                f"Use {selected['id']} for Nesti's planner and coder?", default=False
            )):
                _run(["/provider", "model", name, selected["id"]])


def _provider_menu(q) -> None:
    providers = _metadata(["/provider"])
    if providers is None:
        return
    while True:
        choices = []
        for provider in providers:
            title = provider["name"] + (" (Authenticated)" if provider.get("authenticated") is True else "")
            if provider.get("coming_soon"):
                title += " (coming soon)"
            choices.append(q.Choice(title, value=provider))
        choices.append(q.Choice("Back", value="back"))
        selected = _ask(q.select("Choose a provider", choices=choices))
        if selected is None or selected == "back":
            return
        if selected["kind"] == "platform":
            _models_menu(q, selected["name"])
        else:
            print("Consumer account changes here are deferred; existing login/logout commands are unchanged.")


def _ask(question):
    # Questionary cancels on Ctrl-C by default, but not on Escape.
    from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings

    bindings = KeyBindings()
    bindings.add("escape")(lambda event: event.app.exit(result=None))
    question.application.key_bindings = merge_key_bindings([question.application.key_bindings, bindings])
    return question.ask()


def _plugin_menu(q, entry: dict) -> None:
    choices = [q.Choice("Change %s  (%s)" % (s["name"], s["text"]), value=s) for s in entry["settings"]]
    action = "disable" if entry["enabled"] else "enable"
    choices.extend([q.Choice(action.capitalize(), value=action), q.Choice("Back", value="back")])
    selected = _ask(q.select(entry["name"], choices=choices))
    if selected is None or selected == "back":
        return
    if isinstance(selected, str):
        _run(["/plugin", selected, entry["name"]])
        return
    key = selected["name"]
    if selected["choices"]:
        value = _ask(q.select(key, choices=selected["choices"]))
    elif selected["secret"]:
        value = _ask(q.password(key + " (hidden)"))
    else:
        value = _ask(q.text(key, validate=lambda v: bool(nesti_plugins.SETTING_VALUE_RE.fullmatch(v))
                           or "1-128 chars, no whitespace, quotes, #, $ or \\"))
    if not value:
        return
    args = ["/plugin", "settings", entry["name"], key]
    if selected["secret"]:
        _run(args + ["-"], stdin_text=value + "\n")
    else:
        _run(args + [value])


def main() -> int:
    """Run the optional host menu; cancellation exits without changing anything."""
    import questionary as q

    try:
        while True:
            running = _orchestrator_running()
            choices = [q.Separator("── Plugins ──")]
            try:
                entries = nesti_plugins.plugin_overview(nesti_plugins.Paths(ROOT))
            except nesti_plugins.PluginError as exc:
                entries = None
                choices.append(q.Choice("Plugins: %s" % exc, disabled="Cannot read plugin registry"))
            if entries == []:
                choices.append(q.Choice("No plugins installed (nesti /plugin install <url>)", disabled="No plugins"))
            for entry in entries or []:
                title = "%s (%s)" % (entry["name"], "enabled" if entry["enabled"] else "disabled")
                if entry["settings"]:
                    title += "  " + "; ".join(s["text"] for s in entry["settings"])
                if entry["error"]:
                    title += "  error: " + entry["error"]
                choices.append(q.Choice(title, value=entry))
            for heading, actions in (
                ("Providers", [("Provider status", "/provider"), ("Log in to a provider", "login"),
                               ("Log out of a provider", "logout"), ("Usage and quota", "/usage")]),
                ("Project", [("Statistics page", "/stats"), ("Architecture page", "/arch"),
                             ("Rebuild conventions (Laravel Boost; calls an LLM)", "/boost")]),
            ):
                choices.append(q.Separator("── %s ──" % heading))
                choices.extend(q.Choice(title, value=action, disabled=False if running else NOT_RUNNING)
                               for title, action in actions)
            choices.append(q.Choice("Exit", value="exit"))
            selected = _ask(q.select("What do you want to do?", choices=choices))
            if selected is None or selected == "exit":
                return 0
            if isinstance(selected, dict):
                _plugin_menu(q, selected)
            elif selected == "/provider":
                _provider_menu(q)
            elif selected in ("login", "logout"):
                consumers = _consumers()
                if consumers is None:
                    continue
                names = [name for name, authenticated in consumers if selected == "login" or authenticated]
                if not names:
                    print("No consumer provider is logged in." if selected == "logout" else "No consumer providers found.")
                    continue
                name = _ask(q.select("Choose a provider", choices=names))
                if name and (selected == "login" or _ask(q.confirm("Log out of %s?" % name, default=False))):
                    _run(["/provider", selected, name])
            elif selected != "/boost" or _ask(q.confirm(
                    "Run Laravel Boost discovery? It calls an LLM and rebuilds <NESTI_PROJECT_PATH>/.omp", default=False)):
                _run([selected])
    except Exception as exc:
        if type(exc).__name__ != "NoConsoleScreenBufferError":
            raise
        print("nesti: the menu needs a Windows console (Windows Terminal) or 'winpty nesti'; "
              "every 'nesti <command>' still works.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
