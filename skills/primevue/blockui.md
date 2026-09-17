# BlockUI

BlockUI can either block other components or the whole page.

## Basic

The element to block should be placed as a child of BlockUI and blocked property is required to control the state.

```vue
<template>
    <div>
        <div class="mb-4">
            <Button @click="blocked = true" class="me-2" severity="secondary">Block</Button>
            <Button @click="blocked = false" severity="secondary">Unblock</Button>
        </div>
        <BlockUI :blocked="blocked">
            <Panel header="Header">
                <p class="m-0 text-sm">
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
                    consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
                </p>
            </Panel>
        </BlockUI>
    </div>
</template>

<script setup>
import { ref } from "vue";

const blocked = ref(false);
<\/script>
```

## Document

If the target element is not specified, BlockUI blocks the document by default.

```vue
<template>
    <div>
        <BlockUI :blocked="blocked" fullScreen />
        <div class="flex justify-center">
            <Button @click="blockDocument">Block</Button>
        </div>
    </div>
</template>

<script setup>
import { ref } from "vue";

const blocked = ref(false);
const blockDocument = () => {
    blocked.value = true;

    setTimeout(() => {
        blocked.value = false;
    }, 3000);
}
<\/script>
```

## Accessibility

Screen Reader BlockUI manages aria-busy state attribute when the UI gets blocked and unblocked. Any valid attribute is passed to the root element so additional attributes like role and aria-live can be used to define live regions. Keyboard Support Component does not include any interactive elements.

## Block UI API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| blocked | boolean | false | Controls the blocked state. |
| fullScreen | boolean | false | When enabled, the whole document gets blocked. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | BlockUIPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| mask | BlockUIPassThroughOptionType | Used to pass attributes to the mask's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-blockui | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| blockui.border.radius | --p-blockui-border-radius | Border radius of root |
