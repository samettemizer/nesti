# PrimeVue Plugin

Add PrimeVue workflow skills and the PrimeVue MCP server to your AI assistant with one installation.

## Introduction

The PrimeVue Plugin adds PrimeVue skills and the PrimeVue MCP server to Claude Code, Codex, GitHub Copilot, Cursor, or Gemini CLI. Plugins installed through GitHub Copilot CLI are also available in VS Code. Install the plugin when you want the assistant to follow PrimeVue-specific workflows as well as read the current component documentation. The plugin is published from the primefaces/primeui-plugins repository. Use @primeui/cli for the same installation flow across supported assistants, or follow the manual setup for your client.

## What It Installs

Installing the PrimeVue Plugin adds: Seven skills for PrimeVue implementation, setup, theming, accessibility, migration, and troubleshooting. The PrimeVue MCP server, configured with @primevue/mcp . The manifest required by the selected assistant. PrimeNG and PrimeReact are separate plugins. Installing this plugin does not change your application or install PrimeVue dependencies in the project.

## Skills

Each skill covers one type of PrimeVue work. The skills use @primevue/mcp when they need component APIs, examples, setup guides, or usage validation. Skill Use it for primevue-router Choose the PrimeVue skill that matches the task. primevue-component-implementation Choose and implement components, forms, directives, and documented examples. primevue-setup-installation Install and configure PrimeVue in Vue, Vite, or Nuxt applications. primevue-theming-customization Configure presets, tokens, styled or unstyled mode, Tailwind, pass-through, slots, and events. primevue-accessibility-icons Review semantics, keyboard behavior, focus, accessible names, PrimeIcons, and custom icons. primevue-migration Plan and apply changes using the current PrimeVue migration guides. primevue-audit-troubleshooting Find invalid APIs and troubleshoot components, setup, MCP, plugin, or duplicate configurations. Skill names use the primevue- prefix because assistants may keep skills from several plugins in one shared namespace.

## How Skills Work

You do not need to select a skill manually. Describe the PrimeVue task and the router chooses the relevant workflow. The router checks that the project uses Vue and PrimeVue. The selected skill reads only the component or guide information needed for the task. When component metadata is available, the skill validates the final PrimeVue usage. If the documentation does not confirm a setup or API, the skill reports the limitation instead of guessing. After implementation, run the checks required by your project, including type checking, tests, browser behavior, accessibility, and visual review where applicable.

## CLI Setup

Set --tool to the assistant you use. Keep --library primevue when you run the command outside a project or from a project that uses more than one PrimeUI library.

```vue
pnpm dlx @primeui/cli plugin install --tool copilot --library primevue
```

## Lifecycle and Doctor

Use the same CLI to check the installation, update the plugin, or remove it. Each command applies only to PrimeVue in the selected assistant. Run doctor when the plugin or MCP server is not working as expected. It checks the installation, starts the MCP server, confirms the available tools, and tests documentation retrieval and component validation. Checks that an assistant does not expose are reported as unsupported.

```vue
pnpm dlx @primeui/cli plugin status --tool copilot --library primevue
pnpm dlx @primeui/cli plugin update --tool copilot --library primevue
pnpm dlx @primeui/cli plugin remove --tool copilot --library primevue
pnpm dlx @primeui/cli doctor --tool copilot --library primevue

# Machine-readable diagnostics
pnpm dlx @primeui/cli doctor --tool copilot --library primevue --json
```

## Source

Claude Code, Codex, and GitHub Copilot can install the plugin directly from the public marketplace. For manual Cursor or Gemini CLI setup, clone the repository to a location you intend to keep because those clients use the selected plugins/primevue directory after installation.

```vue
git clone --branch main https://github.com/primefaces/primeui-plugins.git ~/primeui-plugins
ls ~/primeui-plugins/plugins/primevue
```

## Claude Code

Add the PrimeUI marketplace, then install only the PrimeVue plugin.

```vue
claude plugin marketplace add primefaces/primeui-plugins
claude plugin install primevue@primeui
claude plugin list --json
```

## Codex

Add the PrimeUI marketplace, inspect its catalog, then install only the PrimeVue plugin. Use the interactive plugin browser to manage enablement.

```vue
codex plugin marketplace add primefaces/primeui-plugins
codex plugin list --available
codex plugin add primevue@primeui
codex plugin list
```

## VS Code Copilot

Install the PrimeVue Plugin through GitHub Copilot CLI. VS Code automatically discovers plugins installed by Copilot CLI, so it does not need a separate plugin configuration.

```vue
copilot plugin marketplace add primefaces/primeui-plugins
copilot plugin install primevue@primeui
```

## Cursor

For local setup, link the PrimeVue plugin directory into Cursor's local-plugin directory. Restart Cursor or run Developer: Reload Window after creating the link.

```vue
mkdir -p ~/.cursor/plugins/local
ln -s ~/primeui-plugins/plugins/primevue ~/.cursor/plugins/local/primevue
```

## Gemini CLI

Validate the PrimeVue extension directory, then install it from the persistent checkout. Do not install from the repository root because it contains plugins for all three PrimeUI libraries.

```vue
gemini extensions validate ~/primeui-plugins/plugins/primevue
gemini extensions install ~/primeui-plugins/plugins/primevue --consent
gemini extensions list --output-format json
```
