# Breadcrumb

Breadcrumb provides contextual information about page hierarchy.

## Basic

Shows the current location within a navigational hierarchy.

```vue
<template>
    <div class="flex justify-center">
        <Breadcrumb :model="items" :home="home" />
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Bolt from '@primeicons/vue/bolt';
import Home from '@primeicons/vue/home';

const items = ref([
    { label: 'Products' },
    { icon: Bolt, label: 'Electronics' },
    { label: 'Laptops' },
    { label: 'Dell' }
]);
const home = ref({ icon: Home });
<\/script>
```

## Route

A breadcrumb can be used with routing libraries to navigate between pages.

```vue
<template>
    <div class="flex justify-center">
        <Breadcrumb :home="home" :model="items">
            <template #item="{ item, icon, label }">
                <span v-if="item.current" class="p-breadcrumb-item-link font-semibold">{{ label }}</span>
                <a v-else-if="icon && !label" class="p-breadcrumb-item-link cursor-pointer" @click="navigate(item)">
                    <component :is="icon" />
                </a>
                <a v-else class="p-breadcrumb-item-link cursor-pointer" @click="navigate(item)">{{ label }}</a>
            </template>
        </Breadcrumb>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import Home from '@primeicons/vue/home';

const allPages = ref([
    { label: 'Home', icon: Home },
    { label: 'Components' },
    { label: 'Form' },
    { label: 'Input' },
    { label: 'InputText' },
    { label: 'Variants' },
    { label: 'Filled' },
    { label: 'Outlined' }
]);
const home = ref(null);
const items = ref([]);

const updateBreadcrumb = (pages) => {
    if (pages.length === 1) {
        home.value = null;
        items.value = [{ label: pages[0].label, current: true }];
    } else {
        home.value = { icon: pages[0].icon };
        items.value = pages.slice(1).map((page, index, arr) => ({
            ...page,
            current: index === arr.length - 1
        }));
    }
};

const navigate = (item) => {
    const index = item.icon && !item.label ? 0 : allPages.value.findIndex((p) => p.label === item.label);

    if (index !== -1) {
        updateBreadcrumb(allPages.value.slice(0, index + 1));
    }
};

onMounted(() => {
    updateBreadcrumb(allPages.value);
});
<\/script>
```

## Custom Separator

A breadcrumb allows customization of the separator between items using the separator template.

```vue
<template>
    <div class="flex justify-center">
        <Breadcrumb :model="items" :home="home">
            <template #separator> / </template>
        </Breadcrumb>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Bolt from '@primeicons/vue/bolt';
import Home from '@primeicons/vue/home';

const items = ref([
    { label: 'Products' },
    { icon: Bolt, label: 'Electronics' },
    { label: 'Laptops' },
    { label: 'Dell' }
]);
const home = ref({ icon: Home });
<\/script>
```

## Ellipsis

An ellipsis can be used to indicate hidden breadcrumb items.

```vue
<template>
    <div class="flex justify-center">
        <Breadcrumb :model="items" :home="home">
            <template #item="{ item, icon }">
                <span v-if="item.current" class="p-breadcrumb-item-link font-semibold">{{ item.label }}</span>
                <a v-else-if="item.icon && !item.label" class="p-breadcrumb-item-link cursor-pointer">
                    <component :is="icon" />
                </a>
                <a v-else class="p-breadcrumb-item-link cursor-pointer flex items-center gap-1">
                    <component :is="icon" v-if="icon" />
                    <span v-if="item.label">{{ item.label }}</span>
                </a>
            </template>
        </Breadcrumb>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import EllipsisH from '@primeicons/vue/ellipsis-h';
import Bolt from '@primeicons/vue/bolt';
import Home from '@primeicons/vue/home';

const items = ref([
    { icon: EllipsisH },
    { icon: Bolt, label: 'Electronics' },
    { label: 'Laptops' },
    { label: 'Dell', current: true }
]);
const home = ref({ icon: Home });
<\/script>
```

## Custom Item

Custom content can be placed inside the items using the item template.

```vue
<template>
    <div class="flex justify-center">
        <Breadcrumb :model="items" :home="home">
            <template #item="{ item, icon }">
                <a class="p-breadcrumb-item-link flex items-center gap-1 cursor-pointer">
                    <component :is="icon" v-if="icon" />
                    <span v-if="item.label">{{ item.label }}</span>
                    <Badge v-if="item.badge" :value="item.badge" shape="circle" />
                </a>
            </template>
        </Breadcrumb>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Bolt from '@primeicons/vue/bolt';
import Desktop from '@primeicons/vue/desktop';
import Home from '@primeicons/vue/home';

const items = ref([
    { label: 'Products' },
    { icon: Bolt, label: 'Electronics' },
    { icon: Desktop, label: 'Computers' },
    { label: 'Laptops', badge: '5' },
    { label: 'Dell' }
]);
const home = ref({ icon: Home, label: 'Home' });
<\/script>
```

## Accessibility

Screen Reader Breadcrumb uses the nav element and since any attribute is passed to the root implicitly aria-labelledby or aria-label can be used to describe the component. Inside an ordered list is used where the list item separators have aria-hidden to be able to ignored by the screen readers. If the last link represents the current route, aria-current is added with "page" as the value. Keyboard Support No special keyboard interaction is needed, all menuitems are focusable based on the page tab sequence.

## Breadcrumb API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| model | MenuItem[] | - | An array of menuitems. |
| home | any | - | Configuration for the home icon. |
| ariaLabel | string | - | Defines a string value that labels an interactive element. |
| ariaLabelledby | string | - | Identifier of the underlying menu element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | BreadcrumbPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| list | BreadcrumbPassThroughOptionType | Used to pass attributes to the list's DOM element. |
| item | BreadcrumbPassThroughOptionType | Used to pass attributes to the  item's DOM element. |
| itemLink | BreadcrumbPassThroughOptionType | Used to pass attributes to the item link's DOM element. |
| itemIcon | BreadcrumbPassThroughOptionType | Used to pass attributes to the item icon's DOM element. |
| itemLabel | BreadcrumbPassThroughOptionType | Used to pass attributes to the item label's DOM element. |
| separator | BreadcrumbPassThroughOptionType | Used to pass attributes to the separator's DOM element. |
| separatorIcon | BreadcrumbPassThroughOptionType | Used to pass attributes to the separator icon's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-breadcrumb | Class name of the root element |
| p-breadcrumb-list | Class name of the list element |
| p-breadcrumb-home-item | Class name of the home item element |
| p-breadcrumb-separator | Class name of the separator element |
| p-breadcrumb-separator-icon | Class name of the separator icon element |
| p-breadcrumb-item | Class name of the item element |
| p-breadcrumb-item-link | Class name of the item link element |
| p-breadcrumb-item-icon | Class name of the item icon element |
| p-breadcrumb-item-label | Class name of the item label element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| breadcrumb.padding | --p-breadcrumb-padding | Padding of root |
| breadcrumb.background | --p-breadcrumb-background | Background of root |
| breadcrumb.gap | --p-breadcrumb-gap | Gap of root |
| breadcrumb.transition.duration | --p-breadcrumb-transition-duration | Transition duration of root |
| breadcrumb.item.color | --p-breadcrumb-item-color | Color of item |
| breadcrumb.item.hover.color | --p-breadcrumb-item-hover-color | Hover color of item |
| breadcrumb.item.border.radius | --p-breadcrumb-item-border-radius | Border radius of item |
| breadcrumb.item.gap | --p-breadcrumb-item-gap | Gap of item |
| breadcrumb.item.icon.color | --p-breadcrumb-item-icon-color | Icon color of item |
| breadcrumb.item.icon.hover.color | --p-breadcrumb-item-icon-hover-color | Icon hover color of item |
| breadcrumb.item.icon.size | --p-breadcrumb-item-icon-size | Icon size of item icon |
| breadcrumb.item.label.font.weight | --p-breadcrumb-item-label-font-weight | Font weight of item label |
| breadcrumb.item.label.font.size | --p-breadcrumb-item-label-font-size | Font size of item label |
| breadcrumb.item.focus.ring.width | --p-breadcrumb-item-focus-ring-width | Focus ring width of item |
| breadcrumb.item.focus.ring.style | --p-breadcrumb-item-focus-ring-style | Focus ring style of item |
| breadcrumb.item.focus.ring.color | --p-breadcrumb-item-focus-ring-color | Focus ring color of item |
| breadcrumb.item.focus.ring.offset | --p-breadcrumb-item-focus-ring-offset | Focus ring offset of item |
| breadcrumb.item.focus.ring.shadow | --p-breadcrumb-item-focus-ring-shadow | Focus ring shadow of item |
| breadcrumb.separator.color | --p-breadcrumb-separator-color | Color of separator |

## Menu Item API
