# Panel

Panel is a container component with an optional content toggle feature.

## Basic

A simple Panel is created with a header property along with the content as children.

```vue
<template>
    <div class="flex justify-center">
        <Panel header="Order Summary" class="max-w-xs w-full">
            <div class="flex flex-col text-sm">
                <div class="flex justify-between">
                    <span class="text-muted-color">Wireless Headphones</span>
                    <span class="text-color font-medium">$79.00</span>
                </div>
                <div class="flex justify-between mt-3">
                    <span class="text-muted-color">Phone Case</span>
                    <span class="text-color font-medium">$15.00</span>
                </div>
                <div class="flex justify-between mt-3">
                    <span class="text-muted-color">Shipping</span>
                    <span class="text-color font-medium">$5.99</span>
                </div>
                <Divider />
                <div class="flex justify-between">
                    <span class="text-color font-semibold">Total</span>
                    <span class="text-color font-semibold">$99.99</span>
                </div>
            </div>
        </Panel>
    </div>
</template>

<script setup>
import Divider from 'primevue/divider';
import Panel from 'primevue/panel';
<\/script>
```

## Toggleable

Content of the panel can be expanded and collapsed using the toggleable property.

```vue
<template>
    <div class="flex justify-center">
        <Panel header="Order Summary" toggleable class="max-w-xs w-full">
            <div class="flex flex-col text-sm">
                <div class="flex justify-between">
                    <span class="text-muted-color">Wireless Headphones</span>
                    <span class="text-color font-medium">$79.00</span>
                </div>
                <div class="flex justify-between mt-3">
                    <span class="text-muted-color">Phone Case</span>
                    <span class="text-color font-medium">$15.00</span>
                </div>
                <div class="flex justify-between mt-3">
                    <span class="text-muted-color">Shipping</span>
                    <span class="text-color font-medium">$5.99</span>
                </div>
                <Divider />
                <div class="flex justify-between">
                    <span class="text-color font-semibold">Total</span>
                    <span class="text-color font-semibold">$99.99</span>
                </div>
            </div>
        </Panel>
    </div>
</template>

<script setup>
import Divider from 'primevue/divider';
import Panel from 'primevue/panel';
<\/script>
```

## Controlled

The collapsed property with two-way binding controls the open state programmatically.

```vue
<template>
    <div class="flex justify-center">
        <div class="space-y-4 max-w-xs w-full">
            <div class="flex gap-2 justify-center">
                <Button :severity="!collapsed ? 'primary' : 'secondary'" @click="collapsed = false">Open</Button>
                <Button :severity="collapsed ? 'primary' : 'secondary'" @click="collapsed = true">Close</Button>
            </div>
            <Panel header="Order Summary" toggleable v-model:collapsed="collapsed">
                <div class="flex flex-col text-sm">
                    <div class="flex justify-between">
                        <span class="text-muted-color">Wireless Headphones</span>
                        <span class="text-color font-medium">$79.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-muted-color">Phone Case</span>
                        <span class="text-color font-medium">$15.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-muted-color">Shipping</span>
                        <span class="text-color font-medium">$5.99</span>
                    </div>
                    <Divider />
                    <div class="flex justify-between">
                        <span class="text-color font-semibold">Total</span>
                        <span class="text-color font-semibold">$99.99</span>
                    </div>
                </div>
            </Panel>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Button from 'primevue/button';
import Divider from 'primevue/divider';
import Panel from 'primevue/panel';

const collapsed = ref(false);
<\/script>
```

## Indicator

The toggleicon slot customizes the indicator. It can switch between two icons using the collapsed context variable, or render a single icon that animates purely with CSS by targeting the toggle button's aria-expanded state.

```vue
<template>
    <div class="flex flex-col gap-8 max-w-xs mx-auto">
        <div>
            <h3 class="text-sm! font-medium! text-surface-500! mb-2">Match open / closed</h3>
            <Panel header="Order Summary" toggleable class="w-full">
                <template #toggleicon="{ collapsed }">
                    <Plus v-if="collapsed" />
                    <Minus v-else />
                </template>
                <div class="flex flex-col text-sm">
                    <div class="flex justify-between">
                        <span class="text-muted-color">Wireless Headphones</span>
                        <span class="text-color font-medium">$79.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-muted-color">Phone Case</span>
                        <span class="text-color font-medium">$15.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-muted-color">Shipping</span>
                        <span class="text-color font-medium">$5.99</span>
                    </div>
                    <Divider />
                    <div class="flex justify-between">
                        <span class="text-color font-semibold">Total</span>
                        <span class="text-color font-semibold">$99.99</span>
                    </div>
                </div>
            </Panel>
        </div>

        <div>
            <h3 class="text-sm! font-medium! text-surface-500! mb-2">CSS-only with data attributes</h3>
            <Panel header="Order Summary" toggleable class="w-full">
                <template #toggleicon>
                    <ChevronDown class="transition-transform duration-200 in-aria-expanded:rotate-180" />
                </template>
                <div class="flex flex-col text-sm">
                    <div class="flex justify-between">
                        <span class="text-muted-color">Wireless Headphones</span>
                        <span class="text-color font-medium">$79.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-muted-color">Phone Case</span>
                        <span class="text-color font-medium">$15.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-muted-color">Shipping</span>
                        <span class="text-color font-medium">$5.99</span>
                    </div>
                    <Divider />
                    <div class="flex justify-between">
                        <span class="text-color font-semibold">Total</span>
                        <span class="text-color font-semibold">$99.99</span>
                    </div>
                </div>
            </Panel>
        </div>
    </div>
</template>

<script setup>
import ChevronDown from '@primeicons/vue/chevron-down';
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';
<\/script>
```

## Template

Header and footer sections can be customized using header and footer templates.

```vue
<template>
    <div class="flex justify-center">
        <Panel toggleable class="max-w-xs w-full" :pt="{ header: 'p-4!' }">
            <template #header>
                <div class="flex items-center gap-2">
                    <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
                    <span class="font-bold">Amy Elsner</span>
                </div>
            </template>
            <template #icons>
                <Button severity="secondary" rounded text>
                    <Cog />
                </Button>
            </template>
            <template #toggleicon="{ collapsed }">
                <ChevronDown :class="collapsed ? 'transition-transform duration-200' : 'transition-transform duration-200 rotate-180'" />
            </template>
            <template #footer>
                <div class="flex flex-wrap items-center justify-between gap-4">
                    <div class="flex items-center gap-2">
                        <Button rounded text>
                            <User />
                        </Button>
                        <Button severity="secondary" rounded text>
                            <Bookmark />
                        </Button>
                    </div>
                    <span class="text-surface-500 dark:text-surface-400 text-sm">Updated 2 hours ago</span>
                </div>
            </template>
            <p class="m-0 text-sm">
                Product designer focused on accessible interfaces, scalable design systems and modern frontend workflows. Passionate about creating intuitive user experiences that balance usability, consistency and performance across platforms.
                Currently exploring AI-assisted UI tooling, component architecture and developer experience improvements to streamline design-to-development collaboration and build more maintainable products.
            </p>
        </Panel>
    </div>
</template>

<script setup>
import Bookmark from '@primeicons/vue/bookmark';
import ChevronDown from '@primeicons/vue/chevron-down';
import Cog from '@primeicons/vue/cog';
import User from '@primeicons/vue/user';
import Avatar from 'primevue/avatar';
import Button from 'primevue/button';
import Panel from 'primevue/panel';
<\/script>
```

## Accessibility

Screen Reader Toggleable panels use a content toggle button at the header that has aria-controls to define the id of the content section along with aria-expanded for the visibility state. The value to read the button defaults to the value of the header property and can be customized by defining an aria-label or aria-labelledby via the toggleButtonProps property. The content uses region , defines an id that matches the aria-controls of the content toggle button and aria-labelledby referring to the id of the header. Content Toggle Button Keyboard Support Key Function tab Moves focus to the next the focusable element in the page tab sequence. shift + tab Moves focus to the previous the focusable element in the page tab sequence. enter Toggles the visibility of the content. space Toggles the visibility of the content.

## Panel API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| header | string | - | Header text of the panel. |
| toggleable | boolean | false | Defines if content of panel can be expanded and collapsed. |
| collapsed | boolean | false | Defines the initial state of panel content. |
| toggleButtonProps | object | - | Used to pass the custom value to read for the button inside the component. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | PanelPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| header | PanelPassThroughOptionType | Used to pass attributes to the header's DOM element. |
| title | PanelPassThroughOptionType | Used to pass attributes to the title's DOM element. |
| headerActions | PanelPassThroughOptionType | Used to pass attributes to the header actions' DOM element. |
| pcToggleButton | any | Used to pass attributes to the toggle button button's DOM element. |
| contentContainer | PanelPassThroughOptionType | Used to pass attributes to the content container's DOM element. |
| contentWrapper | PanelPassThroughOptionType | Used to pass attributes to the content wrapper DOM element. |
| content | PanelPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| footer | PanelPassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| transition | PanelPassThroughTransitionType | Used to control Vue Transition API. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-panel | Class name of the root element |
| p-panel-header | Class name of the header element |
| p-panel-title | Class name of the title element |
| p-panel-header-actions | Class name of the header actions element |
| p-panel-toggle-button | Class name of the toggle button element |
| p-panel-content-container | Class name of the content container element |
| p-panel-content | Class name of the content element |
| p-panel-footer | Class name of the footer element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| panel.background | --p-panel-background | Background of root |
| panel.border.color | --p-panel-border-color | Border color of root |
| panel.color | --p-panel-color | Color of root |
| panel.border.radius | --p-panel-border-radius | Border radius of root |
| panel.header.background | --p-panel-header-background | Background of header |
| panel.header.color | --p-panel-header-color | Color of header |
| panel.header.padding | --p-panel-header-padding | Padding of header |
| panel.header.border.color | --p-panel-header-border-color | Border color of header |
| panel.header.border.width | --p-panel-header-border-width | Border width of header |
| panel.header.border.radius | --p-panel-header-border-radius | Border radius of header |
| panel.toggleable.header.padding | --p-panel-toggleable-header-padding | Padding of toggleable header |
| panel.title.font.weight | --p-panel-title-font-weight | Font weight of title |
| panel.title.font.size | --p-panel-title-font-size | Font size of title |
| panel.content.padding | --p-panel-content-padding | Padding of content |
| panel.footer.padding | --p-panel-footer-padding | Padding of footer |
