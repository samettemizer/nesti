# TreeSelect

TreeSelect is a form component to choose from hierarchical data.

## Basic

TreeSelect is used with the v-model property for two-way value binding along with the options collection. Internally Tree component is used so the options model is based on TreeNode API. In single selection mode, value binding should be the key value of a node.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" :options="nodes" placeholder="Select Item" class="md:w-80 w-full" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Multiple

More than one node is selectable by setting selectionMode to multiple . By default in multiple selection mode, metaKey press (e.g. ⌘ ) is necessary to add to existing selections however this can be configured with disabling the metaKeySelection property. Note that in touch enabled devices, TreeSelect always ignores metaKey. In multiple selection mode, value binding should be a key-value pair where key is the node key and value is a boolean to indicate selection.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" :options="nodes" :metaKeySelection="false" selectionMode="multiple" placeholder="Select Item" class="w-full md:w-80" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Checkbox

Selection of multiple nodes via checkboxes is enabled by configuring selectionMode as checkbox .

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" :options="nodes" display="chip" :metaKeySelection="false" selectionMode="checkbox" placeholder="Select Item" class="w-full md:w-80" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Virtual Scroll

VirtualScrolling is an efficient way of rendering the options by displaying a small subset of data in the viewport at any time. When dealing with huge number of options, it is suggested to enable VirtualScrolling to avoid performance issues. Usage is simple as setting virtualScroll property to true and defining virtualScrollItemSize to specify the height of an item.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect
            v-model="selectedValue"
            :options="nodes"
            display="chip"
            :metaKeySelection="false"
            selectionMode="checkbox"
            placeholder="Select Item"
            :virtualScroll="true"
            :virtualScrollItemSize="35"
            :virtualScrollOptions="{ scrollHeight: '200px' }"
            class="w-full md:w-80"
        />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getLargeTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Lazy

Lazy loading is useful when dealing with huge datasets, in this example nodes are dynamically loaded on demand using loading property and node-expand method.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" :options="nodes" display="chip" :metaKeySelection="false" selectionMode="checkbox" :loading="loading" loadingMode="icon" @node-expand="onNodeExpand" placeholder="Select Item" class="w-full md:w-80" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const nodes = ref(null);
const selectedValue = ref(null);
const loading = ref(false);

onMounted(() => {
    loading.value = true;
    nodes.value = initiateNodes();

    setTimeout(() => {
        loading.value = false;
    }, 2000);
});

const onNodeExpand = (node) => {
    if (!node.children) {
        node.loading = true;

        setTimeout(() => {
            let _node = { ...node };

            _node.children = [];

            for (let i = 0; i < 3; i++) {
                _node.children.push({
                    key: node.key + '-' + i,
                    label: 'Lazy ' + node.label + '-' + i
                });
            }

            nodes.value[parseInt(node.key, 10)] = { ..._node, loading: false };
        }, 500);
    }
};

const initiateNodes = () => {
    return [
        {
            key: '0',
            label: 'Node 0',
            leaf: false,
            loading: false
        },
        {
            key: '1',
            label: 'Node 1',
            leaf: false,
            loading: false
        },
        {
            key: '2',
            label: 'Node 2',
            leaf: false,
            loading: false
        }
    ];
};
<\/script>
```

## Filter

Filtering is enabled by adding the filter property, by default label property of a node is used to compare against the value in the text field, in order to customize which field(s) should be used during search define filterBy property. In addition filterMode specifies the filtering strategy. In lenient mode when the query matches a node, children of the node are not searched further as all descendants of the node are included. On the other hand, in strict mode when the query matches a node, filtering continues on all descendants.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" :options="nodes" placeholder="Select Item" filter :filterInputAutoFocus="true" class="md:w-80 w-full" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Template

TreeSelect offers multiple slots for customization through templating.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" :options="nodes" placeholder="Select Item" class="md:w-80 w-full">
            <template #dropdownicon>
                <Search />
            </template>
            <template #header>
                <div class="font-medium px-3 py-2">Available Files</div>
            </template>
            <template #footer>
                <div class="px-3 pt-1 pb-2 flex justify-between">
                    <Button severity="secondary" text size="small">
                        <Plus />
                        Add New
                    </Button>
                    <Button severity="danger" text size="small">
                        <Plus />
                        Remove All
                    </Button>
                </div>
            </template>
        </TreeSelect>
    </div>
</template>

<script setup>
import Plus from '@primeicons/vue/plus';
import Search from '@primeicons/vue/search';
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Float Label

A floating label appears on top of the input field when focused. Visit FloatLabel documentation for more information.

```vue
<template>
    <div class="flex flex-wrap justify-center items-end gap-4">
        <FloatLabel class="w-full md:w-80">
            <TreeSelect v-model="value1" inputId="over_label" :options="nodes" class="w-full" />
            <label for="over_label">Over Label</label>
        </FloatLabel>

        <FloatLabel class="w-full md:w-80" variant="in">
            <TreeSelect v-model="value2" inputId="in_label" :options="nodes" class="w-full" />
            <label for="in_label">In Label</label>
        </FloatLabel>

        <FloatLabel class="w-full md:w-80" variant="on">
            <TreeSelect v-model="value3" inputId="on_label" :options="nodes" class="w-full" />
            <label for="on_label">On Label</label>
        </FloatLabel>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const value1 = ref(null);
const value2 = ref(null);
const value3 = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Ifta Label

IftaLabel is used to create infield top aligned labels. Visit IftaLabel documentation for more information.

```vue
<template>
    <div class="flex justify-center">
        <IftaLabel class="w-full md:w-80">
            <TreeSelect v-model="selectedValue" inputId="t_file" :options="nodes" class="w-full" />
            <label for="t_file">File</label>
        </IftaLabel>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Clear Icon

When showClear is enabled, a clear icon is displayed to clear the value.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" showClear :options="nodes" placeholder="Select Item" class="md:w-80 w-full" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Sizes

TreeSelect provides small and large sizes as alternatives to the base.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <TreeSelect v-model="value1" :options="nodes" size="small" placeholder="Small" class="md:w-80 w-full" />
        <TreeSelect v-model="value2" :options="nodes" placeholder="Normal" class="md:w-80 w-full" />
        <TreeSelect v-model="value3" :options="nodes" size="large" placeholder="Large" class="md:w-80 w-full" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const value1 = ref(null);
const value2 = ref(null);
const value3 = ref(null);
const nodes = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Fluid

The fluid prop makes the component take up the full width of its container when set to true.

```vue
<template>
    <div>
        <TreeSelect v-model="selectedValue" :options="nodes" placeholder="Select Item" fluid />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Filled

Specify the variant property as filled to display the component with a higher visual emphasis than the default outlined style.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" variant="filled" :options="nodes" placeholder="Select Item" class="md:w-80 w-full" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused.

```vue
<template>
    <div class="flex justify-center">
        <TreeSelect v-model="selectedValue" disabled class="md:w-80 w-full" :options="nodes" placeholder="TreeSelect" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue = ref(null);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Invalid

The invalid state is applied using the invalid property to indicate failed validation, which can be integrated with form validation libraries.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-4">
        <TreeSelect v-model="selectedValue1" :invalid="selectedValue1 === undefined" :options="nodes" placeholder="TreeSelect" class="md:w-80 w-full" />
        <TreeSelect v-model="selectedValue2" variant="filled" :invalid="selectedValue2 === undefined" :options="nodes" placeholder="TreeSelect" class="md:w-80 w-full" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NodeService } from './service/NodeService';

const nodes = ref(null);
const selectedValue1 = ref(undefined);
const selectedValue2 = ref(undefined);

onMounted(() => {
    NodeService.getTreeNodes().then((data) => (nodes.value = data));
});
<\/script>
```

## Forms

TreeSelect is used with the v-model property.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4 w-full md:w-80">
            <div class="flex flex-col gap-1">
                <TreeSelect name="node" :options="nodes" placeholder="Select Item" fluid />
                <Message v-if="$form.node?.invalid" severity="error" size="small" variant="simple">{{ $form.node.error?.message }}</Message>
            </div>
            <Button type="submit" severity="secondary">Submit</Button>
        </Form>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from "primevue/usetoast";
import { z } from 'zod';
import { NodeService } from '/service/NodeService';

const toast = useToast();
const initialValues = ref({
    node: null
});
const resolver = ref(zodResolver(
    z.object({
        node: z.union([z.record(z.boolean()), z.literal(null)]).refine((obj) => obj !== null && Object.keys(obj).length > 0, { message: 'Selection is required.' })
    })
));

const onFormSubmit = ({ valid }) => {
    if (valid) {
        toast.add({ severity: 'success', summary: 'Form is submitted.', life: 3000 });
    }
};
<\/script>
```

## Accessibility

Screen Reader Value to describe the component can either be provided with aria-labelledby or aria-label props. The treeselect element has a combobox role in addition to aria-haspopup and aria-expanded attributes. The relation between the combobox and the popup is created with aria-controls that refers to the id of the popup. The popup list has an id that refers to the aria-controls attribute of the combobox element and uses tree as the role. Each list item has a treeitem role along with aria-label , aria-selected and aria-expanded attributes. In checkbox selection, aria-checked is used instead of aria-selected . Checkbox and toggle icons are hidden from screen readers as their parent element with treeitem role and attributes are used instead for readers and keyboard support. The container element of a treenode has the group role. The aria-setsize , aria-posinset and aria-level attributes are calculated implicitly and added to each treeitem. If filtering is enabled, filterInputProps can be defined to give aria-* props to the filter input element. Closed State Keyboard Support Key Function tab Moves focus to the treeselect element. space Opens the popup and moves visual focus to the selected treenode, if there is none then first treenode receives the focus. down arrow Opens the popup and moves visual focus to the selected option, if there is none then first option receives the focus. Popup Keyboard Support Key Function tab Moves focus to the next focusable element in the popup, if there is none then first focusable element receives the focus. shift + tab Moves focus to the previous focusable element in the popup, if there is none then last focusable element receives the focus. enter Selects the focused option, closes the popup if selection mode is single. space Selects the focused option, closes the popup if selection mode is single. escape Closes the popup, moves focus to the treeselect element. down arrow Moves focus to the next treenode. up arrow Moves focus to the previous treenode. right arrow If node is closed, opens the node otherwise moves focus to the first child node. left arrow If node is open, closes the node otherwise moves focus to the parent node. Filter Input Keyboard Support Key Function enter Closes the popup and moves focus to the treeselect element. escape Closes the popup and moves focus to the treeselect element. Close Button Keyboard Support Key Function enter Closes the popup and moves focus to the treeselect element. space Closes the popup and moves focus to the treeselect element. escape Closes the popup and moves focus to the treeselect element.

```vue
<template>
    <span id="dd1">Options</span>
    <TreeSelect aria-labelledby="dd1" />

    <TreeSelect aria-label="Options" />
</template>
```

## Tree Select API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | any | - | Value of the component. |
| defaultValue | any | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | The name attribute for the element, typically used in form submissions. |
| options | TreeNode[] | - | An array of treenodes. |
| expandedKeys | any | - | A map of keys to represent the expansion state in controlled mode. |
| showClear | boolean | false | When enabled, a clear icon is displayed to clear the value. |
| clearIcon | string | - | Icon to display in clear button. |
| scrollHeight | string | 20rem | Height of the viewport, a scrollbar is defined if height of list exceeds this value. |
| selectionMode | any | - | Defines the selection mode. |
| fluid | boolean | null | Spans 100% width of the container when enabled. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the overlay gets attached. |
| display | any | comma | Defines how the selected items are displayed. |
| selectedItemsLabel | string | null | Label to display after exceeding max selected labels. |
| maxSelectedLabels | number | - | Decides how many selected item labels to show at most. |
| metaKeySelection | boolean | false | Defines how multiple items can be selected, when true metaKey needs to be pressed to select or unselect an item and when set to false selection of each item can be toggled individually. On touch enabled devices, metaKeySelection is turned off automatically. |
| loading | boolean | false | Whether to display loading indicator. |
| loadingIcon | string | - | Icon to display when tree is loading. |
| loadingMode | any | mask | Loading mode display. |
| filter | boolean | false | When specified, displays an input field to filter the items. |
| filterBy | string \| Function | label | When filtering is enabled, filterBy decides which field or fields (comma separated) to search against. A callable taking a TreeNode can be provided instead of a list of field names. |
| filterMode | any | lenient | Mode for filtering. |
| filterPlaceholder | string | - | Placeholder text to show when filter input is empty. |
| filterLocale | string | - | Locale to use in filtering. The default locale is the host environment's current locale. |
| emptyMessage | string | No available options | Text to display when there are no options available. Defaults to value from PrimeVue locale configuration. |
| placeholder | string | - | Label to display when there are no selections. |
| size | any | - | Defines the size of the component. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| variant | any | null | Specifies the input variant of the component. |
| tabindex | string | - | Index of the element in tabbing order. |
| inputId | string | - | Identifier of the underlying input element. |
| inputClass | string \| object | - | Style class of the input field. |
| inputStyle | object | - | Inline style of the input field. |
| inputProps | InputHTMLAttributes | - | Used to pass all properties of the HTMLInputElement to the focusable input element inside the component. |
| panelClass | any | - | Style class of the overlay panel. |
| ariaLabelledby | string | - | Establishes relationships between the component and label(s) where its value should be one or more element IDs. |
| ariaLabel | string | - | Establishes a string value that labels the component. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TreeSelectPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| labelContainer | TreeSelectPassThroughOptionType | Used to pass attributes to the label container's DOM element. |
| label | TreeSelectPassThroughOptionType | Used to pass attributes to the label's DOM element. |
| clearIcon | TreeSelectPassThroughOptionType | Used to pass attributes to the clear icon's DOM element. |
| chipItem | TreeSelectPassThroughOptionType | Used to pass attributes to the chip's DOM element. |
| pcChip | any | Used to pass attributes to the Chip. |
| dropdown | TreeSelectPassThroughOptionType | Used to pass attributes to the dropdown's DOM element. |
| dropdownIcon | TreeSelectPassThroughOptionType | Used to pass attributes to the dropdown icon's DOM element. |
| panel | TreeSelectPassThroughOptionType | Used to pass attributes to the panel's DOM element. |
| treeContainer | TreeSelectPassThroughOptionType | Used to pass attributes to the tree container's DOM element. |
| pcTree | any | Used to pass attributes to Tree component. |
| emptyMessage | TreeSelectPassThroughOptionType | Used to pass attributes to the empty message's DOM element. |
| hiddenInputContainer | TreeSelectPassThroughOptionType | Used to pass attributes to the hidden input container's DOM element. |
| hiddenInput | TreeSelectPassThroughOptionType | Used to pass attributes to the hidden input's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | TreeSelectPassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-treeselect | Class name of the root element |
| p-treeselect-label-container | Class name of the label container element |
| p-treeselect-label | Class name of the label element |
| p-select-clear-icon | Class name of the clear icon element |
| p-treeselect-chip-item | Class name of the chip item element |
| p-treeselect-chip | Class name of the chip element |
| p-treeselect-dropdown | Class name of the dropdown element |
| p-treeselect-dropdown-icon | Class name of the dropdown icon element |
| p-treeselect-overlay | Class name of the panel element |
| p-treeselect-tree-container | Class name of the tree container element |
| p-treeselect-empty-message | Class name of the empty message element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| treeselect.background | --p-treeselect-background | Background of root |
| treeselect.disabled.background | --p-treeselect-disabled-background | Disabled background of root |
| treeselect.filled.background | --p-treeselect-filled-background | Filled background of root |
| treeselect.filled.hover.background | --p-treeselect-filled-hover-background | Filled hover background of root |
| treeselect.filled.focus.background | --p-treeselect-filled-focus-background | Filled focus background of root |
| treeselect.border.color | --p-treeselect-border-color | Border color of root |
| treeselect.hover.border.color | --p-treeselect-hover-border-color | Hover border color of root |
| treeselect.focus.border.color | --p-treeselect-focus-border-color | Focus border color of root |
| treeselect.invalid.border.color | --p-treeselect-invalid-border-color | Invalid border color of root |
| treeselect.color | --p-treeselect-color | Color of root |
| treeselect.disabled.color | --p-treeselect-disabled-color | Disabled color of root |
| treeselect.placeholder.color | --p-treeselect-placeholder-color | Placeholder color of root |
| treeselect.invalid.placeholder.color | --p-treeselect-invalid-placeholder-color | Invalid placeholder color of root |
| treeselect.shadow | --p-treeselect-shadow | Shadow of root |
| treeselect.padding.x | --p-treeselect-padding-x | Padding x of root |
| treeselect.padding.y | --p-treeselect-padding-y | Padding y of root |
| treeselect.border.radius | --p-treeselect-border-radius | Border radius of root |
| treeselect.focus.ring.width | --p-treeselect-focus-ring-width | Focus ring width of root |
| treeselect.focus.ring.style | --p-treeselect-focus-ring-style | Focus ring style of root |
| treeselect.focus.ring.color | --p-treeselect-focus-ring-color | Focus ring color of root |
| treeselect.focus.ring.offset | --p-treeselect-focus-ring-offset | Focus ring offset of root |
| treeselect.focus.ring.shadow | --p-treeselect-focus-ring-shadow | Focus ring shadow of root |
| treeselect.transition.duration | --p-treeselect-transition-duration | Transition duration of root |
| treeselect.sm.font.size | --p-treeselect-sm-font-size | Sm font size of root |
| treeselect.sm.padding.x | --p-treeselect-sm-padding-x | Sm padding x of root |
| treeselect.sm.padding.y | --p-treeselect-sm-padding-y | Sm padding y of root |
| treeselect.lg.font.size | --p-treeselect-lg-font-size | Lg font size of root |
| treeselect.lg.padding.x | --p-treeselect-lg-padding-x | Lg padding x of root |
| treeselect.lg.padding.y | --p-treeselect-lg-padding-y | Lg padding y of root |
| treeselect.font.weight | --p-treeselect-font-weight | Font weight of root |
| treeselect.font.size | --p-treeselect-font-size | Font size of root |
| treeselect.dropdown.width | --p-treeselect-dropdown-width | Width of dropdown |
| treeselect.dropdown.color | --p-treeselect-dropdown-color | Color of dropdown |
| treeselect.overlay.background | --p-treeselect-overlay-background | Background of overlay |
| treeselect.overlay.border.color | --p-treeselect-overlay-border-color | Border color of overlay |
| treeselect.overlay.border.radius | --p-treeselect-overlay-border-radius | Border radius of overlay |
| treeselect.overlay.color | --p-treeselect-overlay-color | Color of overlay |
| treeselect.overlay.shadow | --p-treeselect-overlay-shadow | Shadow of overlay |
| treeselect.tree.padding | --p-treeselect-tree-padding | Padding of tree |
| treeselect.clear.icon.color | --p-treeselect-clear-icon-color | Color of clear icon |
| treeselect.empty.message.padding | --p-treeselect-empty-message-padding | Padding of empty message |
| treeselect.chip.border.radius | --p-treeselect-chip-border-radius | Border radius of chip |

## Tree Node API
