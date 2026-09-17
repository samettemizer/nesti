# Badge

Badge is a small status indicator for another element.

## Basic

A small overlay on another element to indicate a count or status.

```vue
<template>
    <div class="flex justify-center">
        <Badge value="Badge" />
    </div>
</template>
```

## Severity

The severity property defines the visual style of a badge.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-2">
        <Badge value="Default" />
        <Badge value="Secondary" severity="secondary" />
        <Badge value="Success" severity="success" />
        <Badge value="Info" severity="info" />
        <Badge value="Warning" severity="warn" />
        <Badge value="Danger" severity="danger" />
        <Badge value="Contrast" severity="contrast" />
    </div>
</template>
```

## Size

Use the size property to change the size of a badge.

```vue
<template>
    <div class="flex flex-wrap items-center justify-center gap-2">
        <Badge value="Small" size="small" />
        <Badge value="Default" />
        <Badge value="Large" size="large" />
        <Badge value="XLarge" size="xlarge" />
    </div>
</template>
```

## Overlay

A badge can be added to any element by encapsulating the content with the OverlayBadge component.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-6">
        <OverlayBadge value="2">
            <Bell :size="24" />
        </OverlayBadge>
        <OverlayBadge value="4" severity="danger">
            <CalendarIcon :size="24" />
        </OverlayBadge>
        <OverlayBadge severity="danger">
            <Envelope :size="24" />
        </OverlayBadge>
    </div>
</template>

<script setup>
import Bell from '@primeicons/vue/bell';
import CalendarIcon from '@primeicons/vue/calendar';
import Envelope from '@primeicons/vue/envelope';
<\/script>
```

## Button

Buttons have built-in support for badges to display a badge inline.

```vue
<template>
    <div class="flex justify-center flex-wrap gap-4">
        <Button type="button">Emails<Badge value="8" severity="secondary" /></Button>
        <Button type="button" variant="outlined"><Users />Messages<Badge value="2" severity="contrast" /></Button>
        <OverlayBadge severity="info" class="animate-pulse">
            <Button type="button" variant="outlined" iconOnly><Bell /></Button>
        </OverlayBadge>
    </div>
</template>

<script setup>
import Bell from '@primeicons/vue/bell';
import Users from '@primeicons/vue/users';
<\/script>
```

## Accessibility

Screen Reader Badge does not include any roles and attributes by default, any attribute is passed to the root element so aria roles and attributes can be added if required. If the badges are dynamic, aria-live may be utilized as well. In case badges need to be tabbable, tabIndex can be added to implement custom key handlers. Keyboard Support Component does not include any interactive elements.

## Badge API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | - | Value to display inside the badge. |
| severity | any | - | Severity type of the badge. |
| size | any | - | Size of the badge, valid options are 'small', 'large', and 'xlarge'. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | BadgePassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-badge | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| badge.border.radius | --p-badge-border-radius | Border radius of root |
| badge.padding | --p-badge-padding | Padding of root |
| badge.font.size | --p-badge-font-size | Font size of root |
| badge.font.weight | --p-badge-font-weight | Font weight of root |
| badge.min.width | --p-badge-min-width | Min width of root |
| badge.height | --p-badge-height | Height of root |
| badge.dot.size | --p-badge-dot-size | Size of dot |
| badge.sm.font.size | --p-badge-sm-font-size | Font size of sm |
| badge.sm.min.width | --p-badge-sm-min-width | Min width of sm |
| badge.sm.height | --p-badge-sm-height | Height of sm |
| badge.lg.font.size | --p-badge-lg-font-size | Font size of lg |
| badge.lg.min.width | --p-badge-lg-min-width | Min width of lg |
| badge.lg.height | --p-badge-lg-height | Height of lg |
| badge.xl.font.size | --p-badge-xl-font-size | Font size of xl |
| badge.xl.min.width | --p-badge-xl-min-width | Min width of xl |
| badge.xl.height | --p-badge-xl-height | Height of xl |
| badge.primary.background | --p-badge-primary-background | Background of primary |
| badge.primary.color | --p-badge-primary-color | Color of primary |
| badge.secondary.background | --p-badge-secondary-background | Background of secondary |
| badge.secondary.color | --p-badge-secondary-color | Color of secondary |
| badge.success.background | --p-badge-success-background | Background of success |
| badge.success.color | --p-badge-success-color | Color of success |
| badge.info.background | --p-badge-info-background | Background of info |
| badge.info.color | --p-badge-info-color | Color of info |
| badge.warn.background | --p-badge-warn-background | Background of warn |
| badge.warn.color | --p-badge-warn-color | Color of warn |
| badge.danger.background | --p-badge-danger-background | Background of danger |
| badge.danger.color | --p-badge-danger-color | Color of danger |
| badge.contrast.background | --p-badge-contrast-background | Background of contrast |
| badge.contrast.color | --p-badge-contrast-color | Color of contrast |

## Overlay Badge API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | - | Value to display inside the badge. |
| severity | any | - | Severity type of the badge. |
| size | any | - | Size of the badge, valid options are 'small', 'large', and 'xlarge'. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | OverlayBadgePassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| pcBadge | any | Used to pass attributes to the Badge. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-overlaybadge | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| overlaybadge.outline.width | --p-overlaybadge-outline-width | Outline width of root |
| overlaybadge.outline.color | --p-overlaybadge-outline-color | Outline color of root |
