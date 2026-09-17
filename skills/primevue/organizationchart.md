# OrganizationChart

OrganizationChart visualizes hierarchical organization data.

## Basic

Displays a hierarchy from the value collection.

```vue
<template>
    <div class="flex items-center justify-center overflow-x-auto">
        <OrganizationChart :value="data" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const data = ref([
    {
        key: '0',
        label: 'Founder',
        children: [
            {
                key: '0-0',
                label: 'Product Lead',
                children: [
                    { key: '0-0-0', label: 'UX/UI Designer' },
                    { key: '0-0-1', label: 'Product Manager' }
                ]
            },
            {
                key: '0-1',
                label: 'Engineering Lead',
                children: [
                    { key: '0-1-0', label: 'Frontend Developer' },
                    { key: '0-1-1', label: 'Backend Developer' }
                ]
            }
        ]
    }
]);
<\/script>
```

## Collapsible

Use the collapsible prop to make nodes collapsible.

```vue
<template>
    <OrganizationChart :value="data" collapsible />
</template>

<script setup>
import { ref } from 'vue';

const data = ref([
    {
        key: '0',
        label: 'Founder',
        children: [
            {
                key: '0-0',
                label: 'Product Lead',
                children: [
                    { key: '0-0-0', label: 'UX/UI Designer' },
                    { key: '0-0-1', label: 'Product Manager' }
                ]
            },
            {
                key: '0-1',
                label: 'Engineering Lead',
                children: [
                    { key: '0-1-0', label: 'Frontend Developer' },
                    { key: '0-1-1', label: 'Backend Developer' }
                ]
            }
        ]
    }
]);
<\/script>
```

## Controlled

Control the collapsed state with v-model:collapsedKeys . A key present with true is collapsed; absent keys stay expanded.

```vue
<template>
    <Button label="Expand all" @click="expandAll" />
    <Button label="Collapse all" @click="collapseAll" />
    <OrganizationChart v-model:collapsedKeys="collapsedKeys" :value="data" collapsible>
        <template #toggleicon="{ collapsed }">
            <Plus v-if="collapsed" />
            <Minus v-else />
        </template>
    </OrganizationChart>
</template>

<script setup>
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';
import { ref } from 'vue';

const data = ref([
    {
        key: '0',
        label: 'Founder',
        children: [
            {
                key: '0-0',
                label: 'Product Lead',
                children: [
                    { key: '0-0-0', label: 'UX/UI Designer' },
                    { key: '0-0-1', label: 'Product Manager' }
                ]
            },
            {
                key: '0-1',
                label: 'Engineering Lead',
                children: [
                    { key: '0-1-0', label: 'Frontend Developer' },
                    { key: '0-1-1', label: 'Backend Developer' }
                ]
            }
        ]
    }
]);
const collapsedKeys = ref({});
const expandAll = () => (collapsedKeys.value = {});
const collapseAll = () => (collapsedKeys.value = { '0': true });
<\/script>
```

## Content

The #default slot customizes the node content. OrganizationChart still renders its own structure around it — the content is placed inside .p-organizationchart-node-content , and the built-in collapse button is preserved. The slot scope exposes node , icon , selected , partialSelected , collapsed , toggleSelection and labelClass . The collapse indicator is customized with the #toggleicon slot, which receives the current collapsed state — shown here with the Plus and Minus icons.

```vue
<template>
    <OrganizationChart v-model:collapsedKeys="collapsedKeys" :value="data">
        <template #default="{ node }">
            <div class="flex items-center gap-2">
                <component :is="node.icon" :size="16" />
                <div><div>{{ node.label }}</div><small>{{ node.description }}</small></div>
            </div>
        </template>
    </OrganizationChart>
</template>

<script setup>
import Cloud from '@primeicons/vue/cloud';
import { ref } from 'vue';

const collapsedKeys = ref({});
const data = ref([
    {
        key: '0',
        label: 'AWS Cloud',
        description: 'us-east-1',
        icon: markRaw(Cloud),
        accent: 'bg-orange-500/10 text-orange-500',
        children: [
            {
                key: '0_0',
                label: 'Compute',
                description: 'Workloads & runtime',
                icon: markRaw(Server),
                accent: 'bg-sky-500/10 text-sky-500',
                children: [
                    { key: '0_0_0', label: 'EC2', description: 'Virtual servers', icon: markRaw(Server), accent: 'bg-sky-500/10 text-sky-500' },
                    { key: '0_0_1', label: 'Lambda', description: 'Serverless functions', icon: markRaw(Bolt), accent: 'bg-sky-500/10 text-sky-500' }
                ]
            },
            {
                key: '0_1',
                label: 'Storage',
                description: 'Data persistence',
                icon: markRaw(Database),
                accent: 'bg-emerald-500/10 text-emerald-500',
                children: [
                    { key: '0_1_0', label: 'S3', description: 'Object storage', icon: markRaw(Box), accent: 'bg-emerald-500/10 text-emerald-500' },
                    { key: '0_1_1', label: 'RDS', description: 'Managed databases', icon: markRaw(Database), accent: 'bg-emerald-500/10 text-emerald-500' }
                ]
            },
            {
                key: '0_2',
                label: 'Networking',
                description: 'Edge & access',
                icon: markRaw(Globe),
                accent: 'bg-violet-500/10 text-violet-500',
                children: [
                    { key: '0_2_0', label: 'CloudFront', description: 'Global CDN', icon: markRaw(Globe), accent: 'bg-violet-500/10 text-violet-500' },
                    { key: '0_2_1', label: 'IAM', description: 'Access policies', icon: markRaw(Shield), accent: 'bg-violet-500/10 text-violet-500' }
                ]
            }
        ]
    }
]);
<\/script>
```

## Single Selection

Set selectionMode to single to keep one node selected. Bind the selection with v-model:selectionKeys .

```vue
<template>
    <span>Selected: {{ selectedKeys.join(', ') || '-' }}</span>
    <OrganizationChart v-model:selectionKeys="selectionKeys" :value="data" selectionMode="single" />
</template>

<script setup>
import { computed, ref } from 'vue';

const selectionKeys = ref({});
const selectedKeys = computed(() => Object.keys(selectionKeys.value).filter((key) => selectionKeys.value[key]));
const data = ref([
    {
        key: '0',
        label: 'Founder',
        children: [
            {
                key: '0-0',
                label: 'Product Lead',
                children: [
                    { key: '0-0-0', label: 'UX/UI Designer' },
                    { key: '0-0-1', label: 'Product Manager' }
                ]
            },
            {
                key: '0-1',
                label: 'Engineering Lead',
                children: [
                    { key: '0-1-0', label: 'Frontend Developer' },
                    { key: '0-1-1', label: 'Backend Developer' }
                ]
            }
        ]
    }
]);
<\/script>
```

## Multiple Selection

With multiple , each node toggles independently.

```vue
<template>
    <span>Selected: {{ selectedKeys.join(', ') || '-' }}</span>
    <OrganizationChart v-model:selectionKeys="selectionKeys" :value="data" selectionMode="multiple" />
</template>

<script setup>
import { computed, ref } from 'vue';

const selectionKeys = ref({});
const selectedKeys = computed(() => Object.keys(selectionKeys.value).filter((key) => selectionKeys.value[key]));
const data = ref([
    {
        key: '0',
        label: 'Founder',
        children: [
            {
                key: '0-0',
                label: 'Product Lead',
                children: [
                    { key: '0-0-0', label: 'UX/UI Designer' },
                    { key: '0-0-1', label: 'Product Manager' }
                ]
            },
            {
                key: '0-1',
                label: 'Engineering Lead',
                children: [
                    { key: '0-1-0', label: 'Frontend Developer' },
                    { key: '0-1-1', label: 'Backend Developer' }
                ]
            }
        ]
    }
]);
<\/script>
```

## Checkbox Selection

Checkbox selection cascades to descendants and reflects partial selection on ancestors.

```vue
<template>
    <OrganizationChart v-model:selectionKeys="selectionKeys" :value="data" selectionMode="checkbox" />
</template>

<script setup>
import { ref } from 'vue';

const selectionKeys = ref({});
const data = ref([
    {
        key: '0',
        label: 'Founder',
        children: [
            {
                key: '0-0',
                label: 'Product Lead',
                children: [
                    { key: '0-0-0', label: 'UX/UI Designer' },
                    { key: '0-0-1', label: 'Product Manager' }
                ]
            },
            {
                key: '0-1',
                label: 'Engineering Lead',
                children: [
                    { key: '0-1-0', label: 'Frontend Developer' },
                    { key: '0-1-1', label: 'Backend Developer' }
                ]
            }
        ]
    }
]);
<\/script>
```

## Accessibility

Screen Reader Component uses ARIA roles and attributes for screen reader accessibility. The root element has role="tree" with aria-multiselectable for multiple selection support. Each tree item uses role="treeitem" with aria-level for hierarchy, aria-expanded for collapse state, and aria-selected for selection state. Child nodes are grouped with role="group" . Keyboard Support Node Key Function tab Moves focus through the focusable nodes within the chart. enter Toggles the selection state of a node. space Toggles the selection state of a node. Collapse Button Key Function tab Moves focus through the focusable elements within the chart. enter Toggles the expanded state of a node. space Toggles the expanded state of a node.

## Organization Chart API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | OrganizationChartNode \| OrganizationChartNode[] | - | Value of the component. Accepts a single root node or an array of root nodes. |
| selectionKeys | OrganizationChartSelectionKeys | - | A map of keys to control the selection state. |
| selectionMode | any | - | Type of the selection. When unset, selection is disabled and nodes are not focusable. |
| collapsible | boolean | false | Whether nodes with children render an expand/collapse toggle. |
| collapsedKeys | OrganizationChartCollapsedKeys | - | A map of keys to represent the collapsed state in controlled mode. A key with  `true`  is collapsed; absent keys are expanded. |
| selectable | boolean | true | Whether the nodes are selectable when a selection mode is set. Individual nodes can still opt out via  `node.selectable = false` . |
| gap | number \| number[] | [40, 56] | Horizontal and vertical spacing between nodes, in pixels. A single number applies to both axes. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | OrganizationChartPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| subtree | OrganizationChartPassThroughOptionType | Used to pass attributes to the subtree  `ul` 's DOM element (appears on both the root subtree and every nested subtree). |
| tree | OrganizationChartPassThroughOptionType | Used to pass attributes to the tree  `li` 's DOM element. |
| node | OrganizationChartPassThroughOptionType | Used to pass attributes to the node's DOM element. |
| content | OrganizationChartPassThroughOptionType | Used to pass attributes to the node content's DOM element. |
| pcCheckbox | OrganizationChartPassThroughOptionType | Used to pass attributes to the Checkbox component in checkbox selection mode. |
| label | OrganizationChartPassThroughOptionType | Used to pass attributes to the fallback node label's DOM element. |
| toggle | OrganizationChartPassThroughOptionType | Used to pass attributes to the node toggle button's DOM element. |
| toggleIndicator | OrganizationChartPassThroughOptionType | Used to pass attributes to the fallback node toggle indicator's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-organizationchart | Class name of the root element |
| p-organizationchart-subtree | Class name of the subtree ( `ul` ) element. The top-level subtree also carries  `p-organizationchart-subtree-root` . |
| p-organizationchart-tree | Class name of the tree item ( `li` ) element |
| p-organizationchart-node | Class name of the node element |
| p-organizationchart-node-content | Class name of the node content element |
| p-organizationchart-node-label | Class name of the node label element |
| p-organizationchart-node-toggle-button | Class name of the node toggle button element |
| p-organizationchart-node-toggle-button-icon | Class name of the node toggle indicator element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| organizationchart.gutter | --p-organizationchart-gutter | Gutter of root |
| organizationchart.transition.duration | --p-organizationchart-transition-duration | Transition duration of root |
| organizationchart.node.background | --p-organizationchart-node-background | Background of node |
| organizationchart.node.hover.background | --p-organizationchart-node-hover-background | Hover background of node |
| organizationchart.node.selected.background | --p-organizationchart-node-selected-background | Selected background of node |
| organizationchart.node.border.color | --p-organizationchart-node-border-color | Border color of node |
| organizationchart.node.color | --p-organizationchart-node-color | Color of node |
| organizationchart.node.selected.color | --p-organizationchart-node-selected-color | Selected color of node |
| organizationchart.node.hover.color | --p-organizationchart-node-hover-color | Hover color of node |
| organizationchart.node.padding | --p-organizationchart-node-padding | Padding of node |
| organizationchart.node.toggleable.padding | --p-organizationchart-node-toggleable-padding | Toggleable padding of node |
| organizationchart.node.border.radius | --p-organizationchart-node-border-radius | Border radius of node |
| organizationchart.node.font.size | --p-organizationchart-node-font-size | Font size of node |
| organizationchart.node.font.weight | --p-organizationchart-node-font-weight | Font weight of node |
| organizationchart.node.focus.ring.width | --p-organizationchart-node-focus-ring-width | Focus ring width of node |
| organizationchart.node.focus.ring.style | --p-organizationchart-node-focus-ring-style | Focus ring style of node |
| organizationchart.node.focus.ring.color | --p-organizationchart-node-focus-ring-color | Focus ring color of node |
| organizationchart.node.focus.ring.offset | --p-organizationchart-node-focus-ring-offset | Focus ring offset of node |
| organizationchart.node.focus.ring.shadow | --p-organizationchart-node-focus-ring-shadow | Focus ring shadow of node |
| organizationchart.node.toggle.button.background | --p-organizationchart-node-toggle-button-background | Background of node toggle button |
| organizationchart.node.toggle.button.hover.background | --p-organizationchart-node-toggle-button-hover-background | Hover background of node toggle button |
| organizationchart.node.toggle.button.border.color | --p-organizationchart-node-toggle-button-border-color | Border color of node toggle button |
| organizationchart.node.toggle.button.color | --p-organizationchart-node-toggle-button-color | Color of node toggle button |
| organizationchart.node.toggle.button.hover.color | --p-organizationchart-node-toggle-button-hover-color | Hover color of node toggle button |
| organizationchart.node.toggle.button.size | --p-organizationchart-node-toggle-button-size | Size of node toggle button |
| organizationchart.node.toggle.button.border.radius | --p-organizationchart-node-toggle-button-border-radius | Border radius of node toggle button |
| organizationchart.node.toggle.button.focus.ring.width | --p-organizationchart-node-toggle-button-focus-ring-width | Focus ring width of node toggle button |
| organizationchart.node.toggle.button.focus.ring.style | --p-organizationchart-node-toggle-button-focus-ring-style | Focus ring style of node toggle button |
| organizationchart.node.toggle.button.focus.ring.color | --p-organizationchart-node-toggle-button-focus-ring-color | Focus ring color of node toggle button |
| organizationchart.node.toggle.button.focus.ring.offset | --p-organizationchart-node-toggle-button-focus-ring-offset | Focus ring offset of node toggle button |
| organizationchart.node.toggle.button.focus.ring.shadow | --p-organizationchart-node-toggle-button-focus-ring-shadow | Focus ring shadow of node toggle button |
| organizationchart.node.toggle.button.icon.size | --p-organizationchart-node-toggle-button-icon-size | Icon size of node toggle button |
| organizationchart.connector.color | --p-organizationchart-connector-color | Color of connector |
| organizationchart.connector.border.radius | --p-organizationchart-connector-border-radius | Border radius of connector |
| organizationchart.connector.height | --p-organizationchart-connector-height | Height of connector |
