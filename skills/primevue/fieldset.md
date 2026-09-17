# Fieldset

Fieldset is a grouping component with a content toggle feature.

## Basic

A simple Fieldset is created with a legend property along with the content as children.

```vue
<template>
    <div class="flex justify-center">
        <Fieldset legend="Invoice #1024" class="max-w-xs w-full">
            <div class="flex flex-col text-sm p-2">
                <div class="flex justify-between">
                    <span class="text-color">Design Service</span>
                    <span class="text-muted-color">$120.00</span>
                </div>
                <div class="flex justify-between mt-3">
                    <span class="text-color">Hosting</span>
                    <span class="text-muted-color">$30.00</span>
                </div>
                <Divider />
                <div class="flex justify-between">
                    <span class="text-color font-medium">Total</span>
                    <span class="text-color font-medium">$150.00</span>
                </div>
            </div>
        </Fieldset>
    </div>
</template>

<script setup>
<\/script>
```

## Toggleable

Content of the fieldset can be expanded and collapsed using the toggleable property.

```vue
<template>
    <div class="flex justify-center">
        <Fieldset legend="Invoice #1024" :toggleable="true" class="max-w-xs w-full">
            <div class="flex flex-col text-sm p-2">
                <div class="flex justify-between">
                    <span class="text-color">Design Service</span>
                    <span class="text-muted-color">$120.00</span>
                </div>
                <div class="flex justify-between mt-3">
                    <span class="text-color">Hosting</span>
                    <span class="text-muted-color">$30.00</span>
                </div>
                <Divider />
                <div class="flex justify-between">
                    <span class="text-color font-medium">Total</span>
                    <span class="text-color font-medium">$150.00</span>
                </div>
            </div>
        </Fieldset>
    </div>
</template>

<script setup>
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
            <Fieldset legend="Invoice #1024" :toggleable="true" v-model:collapsed="collapsed">
                <div class="flex flex-col text-sm p-2">
                    <div class="flex justify-between">
                        <span class="text-color">Design Service</span>
                        <span class="text-muted-color">$120.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-color">Hosting</span>
                        <span class="text-muted-color">$30.00</span>
                    </div>
                    <Divider />
                    <div class="flex justify-between">
                        <span class="text-color font-medium">Total</span>
                        <span class="text-color font-medium">$150.00</span>
                    </div>
                </div>
            </Fieldset>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

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
            <Fieldset legend="Invoice #1024" :toggleable="true" class="w-full">
                <template #toggleicon="{ collapsed }">
                    <Plus v-if="collapsed" />
                    <Minus v-else />
                </template>
                <div class="flex flex-col text-sm p-2">
                    <div class="flex justify-between">
                        <span class="text-color">Design Service</span>
                        <span class="text-muted-color">$120.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-color">Hosting</span>
                        <span class="text-muted-color">$30.00</span>
                    </div>
                    <Divider />
                    <div class="flex justify-between">
                        <span class="text-color font-medium">Total</span>
                        <span class="text-color font-medium">$150.00</span>
                    </div>
                </div>
            </Fieldset>
        </div>

        <div>
            <h3 class="text-sm! font-medium! text-surface-500! mb-2">CSS-only with data attributes</h3>
            <Fieldset legend="Invoice #1024" :toggleable="true" class="w-full">
                <template #toggleicon>
                    <ChevronDown class="transition-transform duration-200 in-aria-expanded:rotate-180" />
                </template>
                <div class="flex flex-col text-sm p-2">
                    <div class="flex justify-between">
                        <span class="text-color">Design Service</span>
                        <span class="text-muted-color">$120.00</span>
                    </div>
                    <div class="flex justify-between mt-3">
                        <span class="text-color">Hosting</span>
                        <span class="text-muted-color">$30.00</span>
                    </div>
                    <Divider />
                    <div class="flex justify-between">
                        <span class="text-color font-medium">Total</span>
                        <span class="text-color font-medium">$150.00</span>
                    </div>
                </div>
            </Fieldset>
        </div>
    </div>
</template>

<script setup>
import ChevronDown from '@primeicons/vue/chevron-down';
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';
<\/script>
```

## Accessibility

Screen Reader Fieldset component uses the semantic fieldset element. When toggleable option is enabled, a clickable element with button role is included inside the legend element, this button has aria-controls to define the id of the content section along with aria-expanded for the visibility state. The value to read the button defaults to the value of the legend property and can be customized by defining an aria-label or aria-labelledby via the toggleButtonProps property. The content uses region , defines an id that matches the aria-controls of the content toggle button and aria-labelledby referring to the id of the header. Content Toggle Button Keyboard Support Key Function tab Moves focus to the next the focusable element in the page tab sequence. shift + tab Moves focus to the previous the focusable element in the page tab sequence. enter Toggles the visibility of the content. space Toggles the visibility of the content.

## Fieldset API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| legend | string | - | Header text of the fieldset. |
| toggleable | boolean | false | When specified, content can toggled by clicking the legend. |
| collapsed | boolean | false | Defines the default visibility state of the content. |
| toggleButtonProps | AnchorHTMLAttributes | - | Used to pass the custom value to read for the AnchorHTMLAttributes inside the component. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Slots

| Name |Parameters |Description |
| --- | --- | --- |
| default | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | FieldsetPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| legend | FieldsetPassThroughOptionType | Used to pass attributes to the legend's DOM element. |
| toggleButton | FieldsetPassThroughOptionType | Used to pass attributes to the toggle button's DOM element. |
| toggleIcon | FieldsetPassThroughOptionType | Used to pass attributes to the toggle icon's DOM element. |
| legendLabel | FieldsetPassThroughOptionType | Used to pass attributes to the legend label's DOM element. |
| contentContainer | FieldsetPassThroughOptionType | Used to pass attributes to the content container's DOM element. |
| contentWrapper | FieldsetPassThroughOptionType | Used to pass attributes to the content wrapper DOM element. |
| content | FieldsetPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | FieldsetPassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-fieldset | Class name of the root element |
| p-fieldset-legend | Class name of the legend element |
| p-fieldset-legend-label | Class name of the legend label element |
| p-fieldset-toggle-icon | Class name of the toggle icon element |
| p-fieldset-content-container | Class name of the content container element |
| p-fieldset-content | Class name of the content element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| fieldset.background | --p-fieldset-background | Background of root |
| fieldset.border.color | --p-fieldset-border-color | Border color of root |
| fieldset.border.radius | --p-fieldset-border-radius | Border radius of root |
| fieldset.color | --p-fieldset-color | Color of root |
| fieldset.padding | --p-fieldset-padding | Padding of root |
| fieldset.transition.duration | --p-fieldset-transition-duration | Transition duration of root |
| fieldset.legend.background | --p-fieldset-legend-background | Background of legend |
| fieldset.legend.hover.background | --p-fieldset-legend-hover-background | Hover background of legend |
| fieldset.legend.color | --p-fieldset-legend-color | Color of legend |
| fieldset.legend.hover.color | --p-fieldset-legend-hover-color | Hover color of legend |
| fieldset.legend.border.radius | --p-fieldset-legend-border-radius | Border radius of legend |
| fieldset.legend.border.width | --p-fieldset-legend-border-width | Border width of legend |
| fieldset.legend.border.color | --p-fieldset-legend-border-color | Border color of legend |
| fieldset.legend.padding | --p-fieldset-legend-padding | Padding of legend |
| fieldset.legend.gap | --p-fieldset-legend-gap | Gap of legend |
| fieldset.legend.font.weight | --p-fieldset-legend-font-weight | Font weight of legend |
| fieldset.legend.font.size | --p-fieldset-legend-font-size | Font size of legend |
| fieldset.legend.focus.ring.width | --p-fieldset-legend-focus-ring-width | Focus ring width of legend |
| fieldset.legend.focus.ring.style | --p-fieldset-legend-focus-ring-style | Focus ring style of legend |
| fieldset.legend.focus.ring.color | --p-fieldset-legend-focus-ring-color | Focus ring color of legend |
| fieldset.legend.focus.ring.offset | --p-fieldset-legend-focus-ring-offset | Focus ring offset of legend |
| fieldset.legend.focus.ring.shadow | --p-fieldset-legend-focus-ring-shadow | Focus ring shadow of legend |
| fieldset.toggle.icon.color | --p-fieldset-toggle-icon-color | Color of toggle icon |
| fieldset.toggle.icon.hover.color | --p-fieldset-toggle-icon-hover-color | Hover color of toggle icon |
| fieldset.content.padding | --p-fieldset-content-padding | Padding of content |
