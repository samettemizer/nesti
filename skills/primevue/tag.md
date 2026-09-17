# Tag

Tag component is used to categorize content.

## Basic

A small label for categorizing or marking items.

```vue
<template>
    <div class="flex items-center justify-center">
        <Tag severity="contrast" value="Highlighted" />
    </div>
</template>
```

## Severity

Severity defines the color of the tag, possible values are success , info , warn and danger in addition to the default theme color.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-2">
        <Tag value="Primary"></Tag>
        <Tag severity="secondary" value="Secondary"></Tag>
        <Tag severity="success" value="Success"></Tag>
        <Tag severity="info" value="Info"></Tag>
        <Tag severity="warn" value="Warn"></Tag>
        <Tag severity="danger" value="Danger"></Tag>
        <Tag severity="contrast" value="Contrast"></Tag>
    </div>
</template>
```

## Pill

Enabling rounded , displays a tag as a pill.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-2">
        <Tag value="Primary" rounded></Tag>
        <Tag severity="secondary" value="Secondary" rounded></Tag>
        <Tag severity="success" value="Success" rounded></Tag>
        <Tag severity="info" value="Info" rounded></Tag>
        <Tag severity="warn" value="Warn" rounded></Tag>
        <Tag severity="danger" value="Danger" rounded></Tag>
        <Tag severity="contrast" value="Contrast" rounded></Tag>
    </div>
</template>
```

## Icon

Place the icon left or right of the label.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-2">
        <Tag>
            <User />
            Primary
        </Tag>
        <Tag severity="secondary">
            <User />
            Secondary
        </Tag>
        <Tag severity="success">
            <Check />
            Success
        </Tag>
        <Tag severity="info">
            <Search />
            Info
        </Tag>
        <Tag severity="warn">
            <ExclamationTriangle />
            Warn
        </Tag>
        <Tag severity="danger">
            <Times />
            Danger
        </Tag>
        <Tag severity="contrast">
            <Cog />
            Contrast
        </Tag>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import Cog from '@primeicons/vue/cog';
import ExclamationTriangle from '@primeicons/vue/exclamation-triangle';
import Search from '@primeicons/vue/search';
import Times from '@primeicons/vue/times';
import User from '@primeicons/vue/user';
<\/script>
```

## Template

Children of the component are passed as the content for templating.

```vue
<template>
    <div class="flex justify-center">
        <Tag class="flex items-center gap-2 px-3" style="border: 2px solid var(--border-color); background: transparent; color: var(--text-color)">
            <img alt="Country" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" class="flag flag-it" style="width: 18px" />
            <span class="text-base">Italy</span>
        </Tag>
    </div>
</template>
```

## Accessibility

Screen Reader Tag does not include any roles and attributes by default, any attribute is passed to the root element so aria roles and attributes can be added if required. If the tags are dynamic, aria-live may be utilized as well. In case badges need to be tabbable, tabIndex can be added to implement custom key handlers. Keyboard Support Component does not include any interactive elements.

## Tag API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | any | - | Value to display inside the tag. |
| severity | any | - | Severity type of the tag. |
| rounded | boolean | false | Whether the corners of the tag are rounded. |
| icon | string | - | Icon of the tag to display next to the value. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TagPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| icon | TagPassThroughOptionType | Used to pass attributes to the icon's DOM element. |
| label | TagPassThroughOptionType | Used to pass attributes to the label's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-tag | Class name of the root element |
| p-tag-icon | Class name of the icon element |
| p-tag-label | Class name of the label element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| tag.font.size | --p-tag-font-size | Font size of root |
| tag.font.weight | --p-tag-font-weight | Font weight of root |
| tag.padding | --p-tag-padding | Padding of root |
| tag.gap | --p-tag-gap | Gap of root |
| tag.border.radius | --p-tag-border-radius | Border radius of root |
| tag.rounded.border.radius | --p-tag-rounded-border-radius | Rounded border radius of root |
| tag.icon.size | --p-tag-icon-size | Size of icon |
| tag.primary.background | --p-tag-primary-background | Background of primary |
| tag.primary.color | --p-tag-primary-color | Color of primary |
| tag.secondary.background | --p-tag-secondary-background | Background of secondary |
| tag.secondary.color | --p-tag-secondary-color | Color of secondary |
| tag.success.background | --p-tag-success-background | Background of success |
| tag.success.color | --p-tag-success-color | Color of success |
| tag.info.background | --p-tag-info-background | Background of info |
| tag.info.color | --p-tag-info-color | Color of info |
| tag.warn.background | --p-tag-warn-background | Background of warn |
| tag.warn.color | --p-tag-warn-color | Color of warn |
| tag.danger.background | --p-tag-danger-background | Background of danger |
| tag.danger.color | --p-tag-danger-color | Color of danger |
| tag.contrast.background | --p-tag-contrast-background | Background of contrast |
| tag.contrast.color | --p-tag-contrast-color | Color of contrast |
