#!/usr/bin/env bash
# Nesti setup wizard: .env, forge check, project checkout, containers, provider logins.
set -Eeuo pipefail

STEP="start"
trap 'echo "install.sh: failed during: $STEP (line $LINENO)" >&2' ERR

usage() {
    cat <<'EOF'
Usage: ./install.sh [--yes] [--help]

Configures Nesti for one GitLab project or GitHub repository and starts its containers.

  --yes   take every default without prompting (defaults come from the
          environment variable of the same name, then .env, then .env.example)
  --help  show this help

Windows: run in Git Bash with Docker Desktop's WSL 2 Linux engine.
Checkout paths accept C:/..., C:\..., or /c/...; containers use the
equivalent /run/desktop/mnt/host/c/... path, saved in .env.
The Windows launcher preserves Docker arguments in new shell sessions.

Examples (non-interactive):
  GITLAB_TOKEN=... GITLAB_PROJECT_PATH=group/project ./install.sh --yes
  NESTI_FORGE=github NESTI_GITHUB_TOKEN=... NESTI_GITHUB_REPOSITORY=owner/repo ./install.sh --yes
EOF
}

YES=0
for arg in "$@"; do
    case "$arg" in
        --yes) YES=1 ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

cd "$(dirname "$(readlink -f "$0")")"
ENV_FILE=.env
CONSUMERS="claude chatgpt-plus antigravity copilot"
INTERACTIVE=0
if [ "$YES" -eq 0 ] && [ -t 0 ]; then INTERACTIVE=1; fi

die() { echo "install.sh: $*" >&2; exit 1; }

WINDOWS=0
case "$(uname -s)" in
    MINGW*|MSYS*)
        WINDOWS=1
        # Docker arguments and saved Linux paths must bypass Git Bash conversion.
        export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
        export MSYS2_ENV_CONV_EXCL="${MSYS2_ENV_CONV_EXCL:+$MSYS2_ENV_CONV_EXCL;}NESTI_ENV_VALUE;NESTI_PROJECT_PATH"
        ;;
esac

# --- 1. Prerequisites --------------------------------------------------------
STEP="prerequisites"
for bin in docker git curl; do
    command -v "$bin" >/dev/null 2>&1 || die "'$bin' is required but not installed."
done
# Host Python: active venv, then ./.venv, then PATH, then the
use_python() { [ -n "$1" ] && "$@" -c 'import sys; sys.exit(sys.version_info < (3, 6))' </dev/null >/dev/null 2>&1 && PYTHON=("$@"); }
use_python "${VIRTUAL_ENV:+$VIRTUAL_ENV/Scripts/python.exe}" || use_python "${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python}" \
    || use_python "$PWD/.venv/Scripts/python.exe" || use_python "$PWD/.venv/bin/python" \
    || use_python python3 || use_python python || use_python py -3 \
    || die "no working Python 3 found (tried \$VIRTUAL_ENV, .venv, python3, python, py -3). Install Python 3 or create .venv; on Windows, turn off the Store 'App execution aliases' for python.exe/python3.exe."
docker info >/dev/null 2>&1 || die "'docker info' failed: start Docker or add your user to the docker group."
if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
elif docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
else
    die "neither 'docker-compose' nor 'docker compose' is available."
fi

# --- 2. .env helpers -----------------------------------------------------------
STEP=".env"
# Prints the value of the first KEY= line of FILE (empty when absent).
file_get() {
    [ -f "$2" ] || return 0
    "${PYTHON[@]}" - "$2" "$1" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(rf"^{re.escape(sys.argv[2])}=(.*)$", text, re.M)
sys.stdout.write(m.group(1) if m else "")  # no newline
PY
}

# Replaces the first KEY= line of .env, else appends it; the value travels in the environment.
env_set() {
    NESTI_ENV_VALUE="$2" "${PYTHON[@]}" - "$ENV_FILE" "$1" <<'PY'
import os, re, sys
path, key, value = sys.argv[1], sys.argv[2], os.environ["NESTI_ENV_VALUE"]
text = open(path, encoding="utf-8").read()
pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
if pattern.search(text):
    text = pattern.sub(lambda _: f"{key}={value}", text, count=1)
else:
    text = text.rstrip("\n") + f"\n{key}={value}\n"
open(path, "w", encoding="utf-8", newline="\n").write(text)
PY
}

# Default for KEY: environment variable, then .env, then .env.example; placeholders fall through to empty.
default_for() {
    local key=$1 value
    value=${!key-}
    is_placeholder "$key" "$value" && value=$(file_get "$key" "$ENV_FILE")
    is_placeholder "$key" "$value" && value=$(file_get "$key" .env.example)
    is_placeholder "$key" "$value" && value=""
    printf '%s' "$value"
}

# is_placeholder KEY VALUE: empty for any key; the old sample host for GITLAB_URL;
# a your_* sample only for secrets and the Telegram chat id (real names may start with your_).
is_placeholder() {
    [ -n "$2" ] || return 0
    case $1 in
        GITLAB_URL) [ "${2%/}" = https://gitlab.yourdomain.com ] ;;
        *_TOKEN|*_API_KEY|TELEGRAM_CHAT_ID) [[ "$2" == your_* ]] ;;
        *) return 1 ;;
    esac
}

# ask KEY "Prompt" [validator] → sets REPLY_VALUE; re-asks interactively, dies with --yes.
ask() {
    local key=$1 prompt=$2 validator=${3:-} def value
    def=$(default_for "$key")
    while :; do
        if [ "$INTERACTIVE" -eq 1 ]; then
            read -r -p "$prompt [$def]: " value || value=""
            value=${value:-$def}
        else
            value=$def
        fi
        if [ -z "$validator" ] || "$validator" "$value"; then
            REPLY_VALUE=$value
            return 0
        fi
        [ "$INTERACTIVE" -eq 1 ] || die "invalid $key: '$value'"
    done
}

# ask_secret KEY "Prompt" [required] → sets REPLY_VALUE; Enter keeps the current value.
ask_secret() {
    local key=$1 prompt=$2 required=${3:-} current value state
    current=$(default_for "$key")
    while :; do
        value=""
        if [ "$INTERACTIVE" -eq 1 ]; then
            if is_placeholder "$key" "$current"; then state="not set"; else state="set, Enter keeps it"; fi
            read -r -s -p "$prompt ($state): " value || value=""
            echo
        fi
        value=${value:-$current}
        if [ -z "$required" ] || ! is_placeholder "$key" "$value"; then
            REPLY_VALUE=$value
            return 0
        fi
        [ "$INTERACTIVE" -eq 1 ] || die "$key is required (set it in the environment or .env)."
    done
}

# yes_no "Question" y|n → status 0 for yes; --yes and non-TTY runs take the default.
yes_no() {
    local answer hint="y/N"
    [ "$2" = y ] && hint="Y/n"
    if [ "$INTERACTIVE" -eq 1 ]; then
        read -r -p "$1 [$hint]: " answer || answer=""
    fi
    answer=${answer:-$2}
    [[ "$answer" =~ ^[Yy] ]]
}

valid_url() { [[ "$1" =~ ^https?://[^/[:space:]]+ ]]; }
valid_project() { [[ "$1" =~ ^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)+$ ]]; }
valid_repository() { [[ "$1" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || { echo "  must be owner/repo" >&2; return 1; }; }
valid_forge() { [ "$1" = gitlab ] || [ "$1" = github ] || { echo "  choose gitlab or github" >&2; return 1; }; }
valid_nonempty() { [ -n "$1" ]; }
# Convert saved Docker Desktop paths back to local paths when re-running setup.
local_project_path() {
    if [ "$WINDOWS" -eq 1 ]; then
        cygpath -m -- "${1#/run/desktop/mnt/host}"
    else
        printf '%s\n' "$1"
    fi
}
valid_path() {
    local path
    path=$(local_project_path "$1") || return 1
    if [ "$WINDOWS" -eq 1 ]; then
        [[ "$path" == [A-Za-z]:/* ]] || { echo "  must be an absolute local drive path (C:/... or /c/...)" >&2; return 1; }
    else
        [[ "$path" == /* ]] || { echo "  must be an absolute path" >&2; return 1; }
    fi
    [ ! -L "$path" ] || { echo "  must not be a symlink" >&2; return 1; }
    [ ! -e "$path" ] || [ -d "$path" ] || { echo "  exists and is not a directory" >&2; return 1; }
}
valid_consumers() {
    local name seen=" "
    [ -n "$1" ] || return 1
    IFS=, read -r -a names <<<"$1"
    for name in "${names[@]}"; do
        [[ " $CONSUMERS " == *" $name "* ]] || { echo "  unknown consumer '$name' (choose from: $CONSUMERS)" >&2; return 1; }
        [[ "$seen" != *" $name "* ]] || { echo "  '$name' listed twice" >&2; return 1; }
        seen="$seen$name "
    done
}

if [ ! -f "$ENV_FILE" ]; then
    cp .env.example "$ENV_FILE"
    echo "Created .env from .env.example."
fi
chmod 600 "$ENV_FILE"

# --- 3. Prompts ----------------------------------------------------------------
STEP="prompts"
ask NESTI_FORGE "Forge (gitlab or github)" valid_forge
NESTI_FORGE=$REPLY_VALUE
if [ "$NESTI_FORGE" = github ]; then
    FORGE_NAME=GitHub
    ask NESTI_GITHUB_URL "GitHub URL" valid_url
    NESTI_GITHUB_URL=${REPLY_VALUE%/}
    ask NESTI_GITHUB_API_URL "GitHub API URL" valid_url
    NESTI_GITHUB_API_URL=${REPLY_VALUE%/}
    ask_secret NESTI_GITHUB_TOKEN "GitHub token (fine-grained PAT of Nesti's bot account)" required
    NESTI_GITHUB_TOKEN=$REPLY_VALUE
    ask NESTI_GITHUB_REPOSITORY "GitHub repository (owner/repo)" valid_repository
    NESTI_GITHUB_REPOSITORY=$REPLY_VALUE
    ask NESTI_GITHUB_DEFAULT_BRANCH "Default branch" valid_nonempty
    NESTI_GITHUB_DEFAULT_BRANCH=$REPLY_VALUE
    ask NESTI_GITHUB_ISSUE_LABEL "Opt-in issue label" valid_nonempty
    NESTI_GITHUB_ISSUE_LABEL=$REPLY_VALUE
    REPO_PATH=$NESTI_GITHUB_REPOSITORY
    PROJECT_URL="$NESTI_GITHUB_URL/$NESTI_GITHUB_REPOSITORY"
    ISSUE_LABEL=$NESTI_GITHUB_ISSUE_LABEL
else
    FORGE_NAME=GitLab
    ask GITLAB_URL "GitLab URL (e.g. https://gitlab.com or https://gitlab.yourdomain.com)" valid_url
    GITLAB_URL=${REPLY_VALUE%/}
    ask_secret GITLAB_TOKEN "GitLab token (api scope)" required
    GITLAB_TOKEN=$REPLY_VALUE
    ask GITLAB_PROJECT_PATH "GitLab project path (namespace/project)" valid_project
    GITLAB_PROJECT_PATH=$REPLY_VALUE
    ask GITLAB_DEFAULT_BRANCH "Default branch" valid_nonempty
    GITLAB_DEFAULT_BRANCH=$REPLY_VALUE
    ask GITLAB_ISSUE_LABEL "Opt-in issue label" valid_nonempty
    GITLAB_ISSUE_LABEL=$REPLY_VALUE
    REPO_PATH=$GITLAB_PROJECT_PATH
    PROJECT_URL="$GITLAB_URL/$GITLAB_PROJECT_PATH"
    ISSUE_LABEL=$GITLAB_ISSUE_LABEL
fi

PROJECT_NAME=${REPO_PATH##*/}
if [ -z "${NESTI_PROJECT_PATH-}" ]; then
    # The saved path only stays the default while it still names this project.
    current_path=$(file_get NESTI_PROJECT_PATH "$ENV_FILE")
    if [ -n "$current_path" ]; then current_path=$(local_project_path "$current_path"); fi
    if [ -n "$current_path" ] && [ "$(basename "$current_path")" = "$PROJECT_NAME" ]; then
        NESTI_PROJECT_PATH=$current_path
    else
        NESTI_PROJECT_PATH="$(dirname "$PWD")/$PROJECT_NAME"
    fi
fi
NESTI_PROJECT_PATH=$(local_project_path "$NESTI_PROJECT_PATH")
ask NESTI_PROJECT_PATH "Local checkout of the project" valid_path
PROJECT_CHECKOUT=$(local_project_path "$REPLY_VALUE")
NESTI_PROJECT_PATH=$PROJECT_CHECKOUT
if [ "$WINDOWS" -eq 1 ]; then
    project_drive=${PROJECT_CHECKOUT:0:1}
    NESTI_PROJECT_PATH="/run/desktop/mnt/host/${project_drive,,}${PROJECT_CHECKOUT:2}"
fi
export NESTI_PROJECT_PATH
ask NESTI_CONSUMER_PRIORITY "Consumer subscriptions priority" valid_consumers
NESTI_CONSUMER_PRIORITY=$REPLY_VALUE

env_set NESTI_FORGE "$NESTI_FORGE"
if [ "$NESTI_FORGE" = github ]; then
    env_set NESTI_GITHUB_URL "$NESTI_GITHUB_URL"
    env_set NESTI_GITHUB_API_URL "$NESTI_GITHUB_API_URL"
    env_set NESTI_GITHUB_TOKEN "$NESTI_GITHUB_TOKEN"
    env_set NESTI_GITHUB_REPOSITORY "$NESTI_GITHUB_REPOSITORY"
    env_set NESTI_GITHUB_DEFAULT_BRANCH "$NESTI_GITHUB_DEFAULT_BRANCH"
    env_set NESTI_GITHUB_ISSUE_LABEL "$NESTI_GITHUB_ISSUE_LABEL"
else
    env_set GITLAB_URL "$GITLAB_URL"
    env_set GITLAB_TOKEN "$GITLAB_TOKEN"
    env_set GITLAB_PROJECT_PATH "$GITLAB_PROJECT_PATH"
    env_set GITLAB_DEFAULT_BRANCH "$GITLAB_DEFAULT_BRANCH"
    env_set GITLAB_ISSUE_LABEL "$GITLAB_ISSUE_LABEL"
    GITLAB_HOST=$("${PYTHON[@]}" -c 'import sys, urllib.parse; print(urllib.parse.urlsplit(sys.argv[1]).hostname, end="")' "$GITLAB_URL")
    GITLAB_REPO_HTTPS="$GITLAB_URL/$GITLAB_PROJECT_PATH.git"
    GITLAB_REPO_SSH="git@$GITLAB_HOST:$GITLAB_PROJECT_PATH.git"
    env_set GITLAB_REPO_HTTPS "$GITLAB_REPO_HTTPS"
    env_set GITLAB_REPO_SSH "$GITLAB_REPO_SSH"
fi
env_set NESTI_PROJECT_PATH "$NESTI_PROJECT_PATH"
env_set NESTI_CONSUMER_PRIORITY "$NESTI_CONSUMER_PRIORITY"

for api in OPENROUTER ANTHROPIC DEEPSEEK; do
    enabled=$(default_for "${api}_API_ENABLED")
    def=n
    [ "$enabled" = true ] && def=y
    if yes_no "Enable the ${api} Platform API (billed per token)?" "$def"; then
        ask_secret "${api}_API_KEY" "${api} API key" required
        env_set "${api}_API_KEY" "$REPLY_VALUE"
        if [ "$api" = OPENROUTER ]; then
            ask OPENROUTER_MODEL "OpenRouter model" valid_nonempty
            env_set OPENROUTER_MODEL "$REPLY_VALUE"
        fi
        env_set "${api}_API_ENABLED" true
    else
        env_set "${api}_API_ENABLED" false
    fi
done

ask_secret TELEGRAM_BOT_TOKEN "Telegram bot token (optional)"
env_set TELEGRAM_BOT_TOKEN "$REPLY_VALUE"
ask TELEGRAM_CHAT_ID "Telegram chat id (optional)"
env_set TELEGRAM_CHAT_ID "$REPLY_VALUE"

# --- 4. Forge check ------------------------------------------------------------
# github_check probe|labels: probe verifies push permission and issues, prints the token owner's login;
# labels creates the three intake labels when missing.
github_check() {
    NESTI_GH_TOKEN=$NESTI_GITHUB_TOKEN NESTI_GH_API=$NESTI_GITHUB_API_URL NESTI_GH_REPO=$NESTI_GITHUB_REPOSITORY \
    NESTI_GH_LABEL=$NESTI_GITHUB_ISSUE_LABEL "${PYTHON[@]}" - "$1" <<'PY'
import json, os, sys, urllib.error, urllib.parse, urllib.request

base = os.environ["NESTI_GH_API"]
repo = os.environ["NESTI_GH_REPO"]
label = os.environ["NESTI_GH_LABEL"]

def call(method, path, body=None, missing_ok=False):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=data, method=method, headers={
        "Authorization": "Bearer " + os.environ["NESTI_GH_TOKEN"], "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if missing_ok and exc.code == 404:
            return None
        sys.exit(f"  {method} {path}: HTTP {exc.code} {exc.read().decode(errors='replace')[:300]}")
    except (urllib.error.URLError, OSError) as exc:
        sys.exit(f"  {method} {path}: {exc}")

if sys.argv[1] == "probe":
    info = call("GET", f"/repos/{repo}")
    if not (info.get("permissions") or {}).get("push"):
        sys.exit(f"  no push permission on {info['full_name']}; the token needs Contents read and write")
    if not info.get("has_issues"):
        sys.exit("  issues are disabled on this repository")
    login = call("GET", "/user")["login"]
    print(f"GitHub: {info['html_url']} (push permission, token owner '{login}')", file=sys.stderr)
    print(login, end="")
else:
    for name in (label, f"{label}::in-progress", f"{label}::pause"):
        if call("GET", f"/repos/{repo}/labels/{urllib.parse.quote(name, safe='')}", missing_ok=True):
            print(f"  Label '{name}' exists.")
        else:
            call("POST", f"/repos/{repo}/labels", {"name": name, "color": "1f75cb"})
            print(f"  Label '{name}' created.")
PY
}

if [ "$NESTI_FORGE" = github ]; then
    STEP="GitHub check"
    GH_LOGIN=$(github_check probe) || die "GitHub check failed."
    # A personal token makes the maintainer's own replies look like Nesti's notes (domain answers never resolve).
    if [ "$INTERACTIVE" -eq 1 ]; then
        yes_no "Is '$GH_LOGIN' a dedicated bot account for Nesti?" n \
            || die "use a dedicated bot account's token: with a personal token your own replies count as Nesti's notes."
    else
        echo "Warning: '$GH_LOGIN' must be a dedicated bot account; with a personal token your own replies count as Nesti's notes." >&2
    fi
    github_check labels || die "GitHub check failed."
else
    STEP="GitLab check"
    NESTI_GL_TOKEN=$GITLAB_TOKEN NESTI_GL_URL=$GITLAB_URL NESTI_GL_PROJECT=$GITLAB_PROJECT_PATH \
    NESTI_GL_LABEL=$GITLAB_ISSUE_LABEL NESTI_GL_VERIFY=$(default_for GITLAB_SSL_VERIFY) \
    "${PYTHON[@]}" - <<'PY' || die "GitLab check failed."
import json, os, ssl, sys, urllib.error, urllib.parse, urllib.request

base = os.environ["NESTI_GL_URL"] + "/api/v4"
project = urllib.parse.quote(os.environ["NESTI_GL_PROJECT"], safe="")
label = os.environ["NESTI_GL_LABEL"]
context = ssl._create_unverified_context() if os.environ["NESTI_GL_VERIFY"].lower() == "false" else None

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=data, method=method, headers={
        "PRIVATE-TOKEN": os.environ["NESTI_GL_TOKEN"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        sys.exit(f"  {method} {path}: HTTP {exc.code} {exc.read().decode(errors='replace')[:300]}")
    except (urllib.error.URLError, OSError) as exc:
        sys.exit(f"  {method} {path}: {exc}")

info = call("GET", f"/projects/{project}")
permissions = info.get("permissions") or {}
level = max((permissions.get(k) or {}).get("access_level", 0) for k in ("project_access", "group_access"))
if level < 30:
    sys.exit(f"  access level {level} on {info['path_with_namespace']}; Developer (30) or higher is required")
if not info.get("issues_enabled"):
    sys.exit("  issues are disabled on this project")
print(f"GitLab: {info['web_url']} (access level {level})")
if info.get("empty_repo"):
    print("  The repository is empty: Nesti will create the first commit.")
labels = call("GET", f"/projects/{project}/labels?search={urllib.parse.quote(label)}&per_page=100")
if any(item["name"] == label for item in labels):
    print(f"  Label '{label}' exists.")
else:
    call("POST", f"/projects/{project}/labels", {"name": label, "color": "#1f75cb"})
    print(f"  Label '{label}' created.")
PY
fi

# --- 5. Project checkout ---------------------------------------------------------
STEP="project checkout"
# The token header reaches git through its environment, scoped to the forge URL: never argv (ps) or .git/config.
clone_https() {  # <forge url> <user:token> <repository url>
    local major minor
    IFS=. read -r major minor _ <<<"$(git --version | awk '{print $3}')"
    (( major > 2 || (major == 2 && minor >= 31) )) \
        || die "git >= 2.31 is required for token-less HTTPS clone (found $(git --version)); use SSH or upgrade git"
    GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="http.$1/.extraHeader" \
        GIT_CONFIG_VALUE_0="Authorization: Basic $(printf '%s' "$2" | base64 -w0)" \
        git clone "$3" "$PROJECT_CHECKOUT"
}
if [ -e "$PROJECT_CHECKOUT" ]; then
    [ -d "$PROJECT_CHECKOUT" ] && [ ! -L "$PROJECT_CHECKOUT" ] \
        || die "$PROJECT_CHECKOUT must be a directory, not a symlink."
    echo "Project checkout: $PROJECT_CHECKOUT (existing)"
else
    if [ "$NESTI_FORGE" = github ]; then
        clone_https "$NESTI_GITHUB_URL" "x-access-token:$NESTI_GITHUB_TOKEN" "$NESTI_GITHUB_URL/$NESTI_GITHUB_REPOSITORY.git"
    elif [ "$(default_for GITLAB_USE_SSH)" = true ]; then
        git clone "$GITLAB_REPO_SSH" "$PROJECT_CHECKOUT"
    else
        clone_https "$GITLAB_URL" "oauth2:$GITLAB_TOKEN" "$GITLAB_REPO_HTTPS"
    fi
    echo "Project checkout: $PROJECT_CHECKOUT (cloned)"
fi

# --- 6. Containers -------------------------------------------------------------
STEP="containers"
mkdir -p state logs
docker image inspect postgres:15 >/dev/null 2>&1 || docker pull postgres:15
# Stats and orchestrator share an image tag; concurrent exports race on a clean install.
COMPOSE_PARALLEL_LIMIT=1 "${COMPOSE[@]}" build
if [ "$WINDOWS" -eq 1 ]; then
    docker run --rm --name "nesti-install-check-$$" --network none \
        --mount "type=bind,source=$NESTI_PROJECT_PATH,target=$NESTI_PROJECT_PATH,readonly" \
        --entrypoint python nesti-orchestrator:latest \
        -c 'import os, sys; assert os.path.isdir(sys.argv[1]), sys.argv[1]' "$NESTI_PROJECT_PATH" \
        || die "project mount failed: use Docker Desktop's WSL 2 Linux engine and a shared local drive."
fi
"${COMPOSE[@]}" up -d

# --- 7. Readiness --------------------------------------------------------------
STEP="readiness"
PROVIDERS=""
for _ in $(seq 1 60); do
    if PROVIDERS=$(docker exec nesti-orchestrator nesti /provider 2>/dev/null); then break; fi
    PROVIDERS=""
    sleep 2
done
if [ -z "$PROVIDERS" ]; then
    "${COMPOSE[@]}" logs --tail 50 nesti-orchestrator >&2 || true
    die "nesti-orchestrator did not answer 'nesti /provider' within 120 s."
fi

# --- 8. Providers --------------------------------------------------------------
STEP="providers"
authenticated() { grep -qE "^[[:space:]]*- $1 \(Authenticated\)" <<<"$PROVIDERS"; }
IFS=, read -r -a wanted <<<"$NESTI_CONSUMER_PRIORITY"
for name in "${wanted[@]}"; do
    authenticated "$name" && continue
    if [ "$INTERACTIVE" -eq 1 ] && yes_no "Log in to $name now?" y; then
        docker exec -it nesti-orchestrator nesti /provider login "$name" || echo "  Login for $name did not finish."
    else
        echo "Log in later: docker exec -it nesti-orchestrator nesti /provider login $name"
    fi
done
PROVIDERS=$(docker exec nesti-orchestrator nesti /provider 2>/dev/null || true)
AUTHED=""
for name in "${wanted[@]}"; do
    if authenticated "$name"; then AUTHED="${AUTHED:+$AUTHED, }$name"; fi
done
if [ -z "$AUTHED" ] && ! grep -qE '^(DEEPSEEK|ANTHROPIC|OPENROUTER)_API_ENABLED=true$' "$ENV_FILE"; then
    echo "Warning: no consumer subscription is logged in and no Platform API is enabled; Nesti cannot call an LLM." >&2
fi

# --- 9. Launcher ---------------------------------------------------------------
STEP="launcher"
LAUNCHER="$HOME/.local/bin/nesti"
TARGET=$(readlink -f scripts/nesti)
if [ "$WINDOWS" -eq 1 ] || [ "$(readlink -f "$LAUNCHER" 2>/dev/null || true)" != "$TARGET" ]; then
    if yes_no "Install $LAUNCHER for scripts/nesti?" y; then
        mkdir -p "$HOME/.local/bin"
        if [ "$WINDOWS" -eq 1 ]; then
            # A new shell needs the Docker argument guard; Git Bash ln may copy instead of linking.
            rm -f "$LAUNCHER"
            printf '#!/usr/bin/env bash\nexport MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"\nexec %q "$@"\n' "$TARGET" > "$LAUNCHER"
            chmod +x "$LAUNCHER"
            "$LAUNCHER" /provider >/dev/null || die "installed launcher could not reach the provider CLI."
        else
            ln -sf "$TARGET" "$LAUNCHER"
        fi
        echo "Installed $LAUNCHER."
    fi
fi
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "Warning: $HOME/.local/bin is not on PATH; add it to use 'nesti'." >&2 ;;
esac

# --- 10. Preflight -------------------------------------------------------------
STEP="preflight"
if [ "$YES" -eq 0 ] && yes_no "Run the preflight check? It creates and closes a probe issue on $FORGE_NAME." n; then
    docker exec nesti-orchestrator python scripts/preflight.py
fi

# --- 11. Summary ---------------------------------------------------------------
STEP="summary"
cat <<EOF

Nesti is installed.
  Project:   $PROJECT_URL
  Checkout:  $PROJECT_CHECKOUT
  Mount:     $NESTI_PROJECT_PATH
  Label:     $ISSUE_LABEL
  Providers: ${AUTHED:-none authenticated}

Next steps:
  - open an issue on the project with the '$ISSUE_LABEL' label
  - follow the run: ${COMPOSE[*]} logs -f nesti-orchestrator
  - usage statistics: nesti /stats
  - architecture view: nesti /arch
EOF
