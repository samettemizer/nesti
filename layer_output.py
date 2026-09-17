"""
layer_output.py – turn raw sandbox output into the part that carries meaning.

A test layer's container output is dominated by dependency-installation
chatter: `composer install` resolving 27 packages, `npm install` reporting
audit advisories and a new npm major, Laravel's package discovery, PrimeVue's
license notice. The actual assertion failure is always at the very END.

Truncating such output from the front — `output[:1000]` — therefore keeps only
the noise and cuts the failure off mid-word. Observed on a real run: a GitLab
issue's failure comment consisted entirely of `added 203 packages`,
`2 high severity vulnerabilities`, `npm notice New major version` and
`[PrimeUI] PrimeUI license is not configured.`, ending at `× resources/js/co`.
The same slice feeds the retry prompt, so the model was shown npm advisories
instead of its own failing test — three attempts in a row.

``condense`` fixes both consumers from one place:
  1. strip ANSI colour escapes (Laravel and PHPUnit emit them; they survived
     into issue comments as literal `[37;44m` noise),
  2. drop known installer/advisory lines,
  3. collapse blank runs,
  4. keep the TAIL, cut on a line boundary.

It is deliberately conservative: a line is dropped only when it matches a
known-noise pattern, and if filtering would leave nothing the raw tail is
returned instead. Losing a real error is far worse than keeping some noise.
"""

import re

# Matches CSI sequences with or without the ESC byte. The optional ESC is
# intentional: some producers (and anything that has already passed through a
# log pipeline) leave the bare `[37;44m` form behind.
_ANSI_RE = re.compile(r"(?:\x1b)?\[[0-9;?]{1,12}[mK]")

# Lines that never help diagnose a failure. Anchored where possible so a real
# message merely containing one of these words is never dropped.
_NOISE_RE = re.compile(
    r"""^(?:
          npm\ notice.*
        | npm\ warn\ deprecated.*
        | added\ \d+\ packages.*
        | removed\ \d+\ packages.*
        | changed\ \d+\ packages.*
        | up\ to\ date\ in\ .*
        | \d+\ packages?\ (?:are|is)\ looking\ for\ funding
        | \ *run\ `npm\ fund`\ for\ details
        | \d+\ (?:low|moderate|high|critical)\ severity\ vulnerabilit(?:y|ies)
        | To\ address\ (?:all\ issues|these\ issues).*
        | Some\ issues\ need\ review.*
        | \ *npm\ audit\ fix.*
        | Run\ `npm\ audit`\ for\ details\.?
        | \[PrimeUI\]\ PrimeUI\ license\ is\ not\ configured\.?
        # ── composer ──────────────────────────────────────────────────────
        | Loading\ composer\ repositories.*
        | Updating\ dependencies
        | Lock\ file\ operations:.*
        | Package\ operations:.*
        | Writing\ lock\ file
        | Installing\ dependencies\ from\ lock\ file.*
        | Verifying\ lock\ file\ contents.*
        | Nothing\ to\ install,\ update\ or\ remove
        | No\ composer\.lock\ file\ present.*
        | Generating\ (?:optimized\ )?autoload\ files
        | \ *-\ (?:Locking|Downloading|Installing|Removing|Upgrading|Downgrading)\ .*
        | \d+\ package\ suggestions\ were\ added.*
        | \d+\ packages\ you\ are\ using\ are\ looking\ for\ funding\.?
        | Use\ the\ `composer\ (?:fund|suggest)`\ command.*
        | >?\ *Illuminate\\Foundation\\ComposerScripts::postAutoloadDump
        | >?\ *@php\ artisan\ package:discover.*
        | \ *INFO\ +Discovering\ packages\.?
        | \ *[a-z0-9._-]+/[a-z0-9._-]+\ [\ .]*DONE.*
        )\s*$""",
    re.VERBOSE,
)

_TRIMMED_MARKER = "[... earlier output trimmed ...]"


def _strip_noise(text: str) -> str:
    """Drop installer chatter and collapse the blank runs it leaves behind."""
    kept: list[str] = []
    for line in text.splitlines():
        if _NOISE_RE.match(line):
            continue
        if not line.strip() and (not kept or not kept[-1].strip()):
            # Swallow leading blanks and runs of more than one blank line.
            continue
        kept.append(line.rstrip())
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept)


def _tail(text: str, limit: int) -> str:
    """
    Return at most *limit* characters from the END, cut on a line boundary.

    The tail is what matters: assertion failures, stack traces and the
    `Tests: N failed` summary all appear last.
    """
    if len(text) <= limit:
        return text
    window = text[-limit:]
    newline = window.find("\n")
    if newline != -1 and newline < len(window) - 1:
        window = window[newline + 1:]
    return f"{_TRIMMED_MARKER}\n{window}"


def condense(output: str, limit: int) -> str:
    """
    Reduce raw sandbox output to at most *limit* meaningful characters.

    Never raises and never returns an empty string for non-empty input: if
    noise filtering removes everything, the unfiltered tail is used instead,
    because dropping a real error is worse than keeping some chatter.
    """
    if not output:
        return ""
    if limit <= 0:
        return ""

    try:
        plain = _ANSI_RE.sub("", output)
        filtered = _strip_noise(plain)
        if not filtered.strip():
            filtered = plain.strip()
        return _tail(filtered, limit)
    except Exception:  # pylint: disable=broad-except
        # Formatting must never be the reason a failure goes unreported.
        return output[-limit:]
