# Popover

Popover is a container component that can overlay other components on page.

## Basic

Popover is accessed via its ref and visibility is controlled using toggle , show and hide functions with an event of the target.

```vue
<template>
    <div class="flex justify-center">
        <Button type="button" severity="secondary" variant="outlined" @click="toggle">Show Popover</Button>
        <Popover ref="op">
            <div class="max-w-72 w-full">
                <div class="flex items-center justify-between">
                    <span class="font-semibold">Create a New Workspace</span>
                </div>
                <p class="text-sm text-muted-color mt-2 mb-0!">Name your workspace to get started. You can always change this later.</p>
                <InputText placeholder="Workspace Name" class="mt-3 w-full" />
                <div class="flex items-center justify-between mt-4">
                    <span class="text-xs text-surface-500 dark:text-surface-400">Lowercase letters and dashes only</span>
                    <div class="flex items-center gap-2">
                        <Button type="button" severity="secondary" variant="outlined" size="small" @click="hide">Cancel</Button>
                        <Button type="button" size="small" @click="hide">Create</Button>
                    </div>
                </div>
            </div>
        </Popover>
    </div>
</template>

<script setup>
import { ref } from "vue";

const op = ref();

const toggle = (event) => {
    op.value.toggle(event);
}

const hide = () => {
    op.value.hide();
}
<\/script>
```

## Controlled

Popover visibility can be controlled from outside by accessing the component with a template ref and calling its show , hide and toggle methods. Pass the trigger element as the second argument to keep the overlay anchored to it.

```vue
<template>
    <div class="flex gap-4 justify-center items-center">
        <Button type="button" @click="toggleFromOutside">Show Popover</Button>
        <Button ref="trigger" type="button" severity="secondary" variant="outlined" @click="toggle">Popover Trigger</Button>
        <Popover ref="op">
            <div class="max-w-72 w-full">
                <div class="flex items-center justify-between">
                    <span class="font-semibold text-sm">Create a New Workspace</span>
                </div>
                <p class="text-sm text-muted-color mt-2 mb-0!">Name your workspace to get started. You can always change this later.</p>
                <InputText placeholder="Workspace Name" class="mt-3 w-full" />
                <div class="flex items-center justify-between mt-4">
                    <span class="text-xs text-surface-500 dark:text-surface-400">Lowercase letters and dashes only</span>
                    <div class="flex items-center gap-2">
                        <Button type="button" severity="secondary" variant="outlined" size="small" @click="hide">Cancel</Button>
                        <Button type="button" size="small" @click="hide">Create</Button>
                    </div>
                </div>
            </div>
        </Popover>
    </div>
</template>

<script setup>
import { ref } from "vue";

const op = ref();
const trigger = ref();

const toggle = (event) => {
    op.value.toggle(event);
}

const toggleFromOutside = (event) => {
    op.value.toggle(event, trigger.value.$el);
}

const hide = () => {
    op.value.hide();
}
<\/script>
```

## Accessibility

Screen Reader Popover component uses dialog role and since any attribute is passed to the root element you may define attributes like aria-label or aria-labelledby to describe the popup contents. In addition aria-modal is added since focus is kept within the popup. It is recommended to use a trigger component that can be accessed with keyboard such as a button, if not adding tabIndex would be necessary. Popover adds aria-expanded state attribute and aria-controls to the trigger so that the relation between the trigger and the popup is defined. Popover Keyboard Support When the popup gets opened, the first focusable element receives the focus and this can be customized by adding autofocus to an element within the popup. Key Function tab Moves focus to the next the focusable element within the popup. shift + tab Moves focus to the previous the focusable element within the popup. escape Closes the popup and moves focus to the trigger. Close Button Keyboard Support Key Function enter Closes the popup and moves focus to the trigger. space Closes the popup and moves focus to the trigger.

## Popover API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dismissable | boolean | true | Enables to hide the overlay when outside is clicked. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the overlay gets attached. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| breakpoints | PopoverBreakpoints | - | Object literal to define widths per screen size. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |
| closeOnEscape | boolean | true | Specifies if pressing escape key should hide the dialog. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | PopoverPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| content | PopoverPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | PopoverPassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-popover | Class name of the root element |
| p-popover-content | Class name of the content element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| popover.background | --p-popover-background | Background of root |
| popover.border.color | --p-popover-border-color | Border color of root |
| popover.color | --p-popover-color | Color of root |
| popover.border.radius | --p-popover-border-radius | Border radius of root |
| popover.shadow | --p-popover-shadow | Shadow of root |
| popover.gutter | --p-popover-gutter | Gutter of root |
| popover.arrow.offset | --p-popover-arrow-offset | Arrow offset of root |
| popover.content.padding | --p-popover-content-padding | Padding of content |
