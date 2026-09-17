# Toolbar

Toolbar is a grouping component for buttons and other content.

## Basic

Combines action buttons and controls in a horizontal bar.

```vue
<template>
    <Toolbar>
        <template #start>
            <Button class="mr-2" variant="text" severity="secondary">
                <Plus />
            </Button>
            <Button class="mr-2" variant="text" severity="secondary">
                <Print />
            </Button>
            <Button variant="text" severity="secondary">
                <Upload />
            </Button>
        </template>

        <template #center>
            <IconField iconPosition="left">
                <InputIcon>
                    <Search />
                </InputIcon>
                <InputText placeholder="Search" />
            </IconField>
        </template>

        <template #end>
            <Button severity="secondary" variant="outlined" size="small">Cancel</Button>
            <Button size="small" class="ml-2">Save</Button>
        </template>
    </Toolbar>
</template>

<script setup>
import Plus from '@primeicons/vue/plus';
import Print from '@primeicons/vue/print';
import Search from '@primeicons/vue/search';
import Upload from '@primeicons/vue/upload';
<\/script>
```

## Custom

A customized toolbar with navigation bar functionality.

```vue
<template>
    <Toolbar class="@container" :style="{ 'border-radius': '3rem', padding: '0.75rem 1rem 0.75rem 1.5rem', background: 'var(--p-surface-900)', border: 'none' }">
        <template #start>
            <div class="flex items-center gap-1">
                <span class="text-xl" style="color: var(--p-primary-400)">
                    <Prime />
                </span>
                <span class="font-bold text-lg ml-2" style="color: var(--p-surface-0)">Brand</span>
            </div>
            <div class="ml-6 hidden @min-[620px]:flex gap-1">
                <Button variant="text" size="small" class="text-surface-0! hover:bg-surface-700!">Products</Button>
                <Button variant="text" size="small" class="text-surface-0! hover:bg-surface-700!">Solutions</Button>
                <Button variant="text" size="small" class="text-surface-0! hover:bg-surface-700!">Resources</Button>
                <Button variant="text" size="small" class="text-surface-0! hover:bg-surface-700!">Pricing</Button>
            </div>
        </template>

        <template #end>
            <div class="flex items-center gap-2">
                <Button variant="text" size="small" iconOnly aria-label="Search" class="text-surface-0! hover:bg-surface-700!">
                    <Search />
                </Button>
                <Button size="small">Get Started</Button>
                <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
            </div>
        </template>
    </Toolbar>
</template>

<script setup>
import Prime from '@primeicons/vue/prime';
import Search from '@primeicons/vue/search';
<\/script>
```

## Accessibility

Screen Reader Toolbar uses toolbar role for the root element, aria-orientation is not included as it defaults to horizontal . Any valid attribute is passed to the root element so you may add additional properties like aria-labelledby and aria-labelled to define the element if required. Keyboard Support Component does not include any interactive elements. Arbitrary content can be placed with templating and elements like buttons inside should follow the page tab sequence.

```vue
<Toolbar aria-label="Actions">
    Content
</Toolbar>
```

## Toolbar API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| ariaLabelledby | string | - | Defines a string value that labels an interactive element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ToolbarPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| start | ToolbarPassThroughOptionType | Used to pass attributes to the start's DOM element. |
| center | ToolbarPassThroughOptionType | Used to pass attributes to the center's DOM element. |
| end | ToolbarPassThroughOptionType | Used to pass attributes to the right's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-toolbar | Class name of the root element |
| p-toolbar-start | Class name of the start element |
| p-toolbar-center | Class name of the center element |
| p-toolbar-end | Class name of the end element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| toolbar.background | --p-toolbar-background | Background of root |
| toolbar.border.color | --p-toolbar-border-color | Border color of root |
| toolbar.border.radius | --p-toolbar-border-radius | Border radius of root |
| toolbar.color | --p-toolbar-color | Color of root |
| toolbar.gap | --p-toolbar-gap | Gap of root |
| toolbar.padding | --p-toolbar-padding | Padding of root |
