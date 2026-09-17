# ContextMenu

ContextMenu displays an overlay menu on right click of its target.

## Basic

ContextMenu is attached to a target element and activated with a right-click.

```vue
<template>
    <div class="flex justify-center">
        <div
            class="flex items-center justify-center w-full max-w-md mx-auto h-40 rounded-md border-2 border-dashed border-surface-200 dark:border-surface-700 text-sm text-surface-500 dark:text-surface-400 select-none"
            @contextmenu="onRightClick"
        >
            Right-click here
        </div>
        <ContextMenu ref="menu" :model="items" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const menu = ref();
const items = ref([
    { label: 'Cut' },
    { label: 'Copy' },
    { label: 'Paste' },
    { label: 'Rename' },
    { separator: true },
    {
        label: 'Delete',
        class: '[&>.p-contextmenu-item-content]:text-red-500! dark:[&>.p-contextmenu-item-content]:text-red-400!'
    }
]);

const onRightClick = (event) => {
    menu.value.show(event);
};
<\/script>
```

## Submenus

Submenus are defined by nesting menu items within the items property of a parent menu item.

```vue
<template>
    <div class="flex justify-center">
        <div
            class="flex items-center justify-center w-full max-w-md mx-auto h-40 rounded-md border-2 border-dashed border-surface-200 dark:border-surface-700 text-sm text-surface-500 dark:text-surface-400 select-none"
            @contextmenu="onRightClick"
        >
            Right-click here
        </div>
        <ContextMenu ref="menu" :model="items" />
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Copy from '@primeicons/vue/copy';
import Download from '@primeicons/vue/download';
import ExternalLink from '@primeicons/vue/external-link';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import Link from '@primeicons/vue/link';
import Send from '@primeicons/vue/send';
import Trash from '@primeicons/vue/trash';

const menu = ref();
const items = ref([
    { label: 'Copy', icon: Copy },
    {
        label: 'Share',
        icon: Link,
        items: [
            { label: 'Send via email', icon: Send },
            { label: 'Copy link', icon: Link },
            { label: 'Open in new tab', icon: ExternalLink }
        ]
    },
    {
        label: 'Save as',
        icon: Download,
        items: [
            { label: 'PDF', icon: File },
            {
                label: 'Image',
                icon: File,
                items: [{ label: 'PNG' }, { label: 'JPG' }, { label: 'WebP' }, { label: 'SVG' }]
            },
            { label: 'ZIP archive', icon: Folder }
        ]
    },
    { separator: true },
    {
        label: 'Delete',
        icon: Trash,
        class: 'text-red-500! dark:text-red-400!'
    }
]);

const onRightClick = (event) => {
    menu.value.show(event);
};
<\/script>
```

## Global

Setting the global property to true attaches the context menu to the document.

```vue
<template>
    <div class="text-center">
        <p class="mb-0 text-sm">Right-click anywhere on this page to view the global ContextMenu.</p>
        <ContextMenu global :model="items" />
    </div>
</template>

<script setup>
import { ref } from 'vue';
import ChartLine from '@primeicons/vue/chart-line';
import Clipboard from '@primeicons/vue/clipboard';
import Copy from '@primeicons/vue/copy';
import ExternalLink from '@primeicons/vue/external-link';
import Folder from '@primeicons/vue/folder';
import Home from '@primeicons/vue/home';
import Print from '@primeicons/vue/print';
import QuestionCircle from '@primeicons/vue/question-circle';
import Refresh from '@primeicons/vue/refresh';
import SearchMinus from '@primeicons/vue/search-minus';
import SearchPlus from '@primeicons/vue/search-plus';

const items = ref([
    { label: 'Back', icon: Home },
    { label: 'Reload', icon: Refresh },
    { separator: true },
    { label: 'Copy', icon: Copy },
    { label: 'Paste', icon: Clipboard },
    { separator: true },
    {
        label: 'View',
        icon: Folder,
        items: [
            { label: 'Zoom In', icon: SearchPlus },
            { label: 'Zoom Out', icon: SearchMinus },
            { label: 'Page Source', icon: ChartLine }
        ]
    },
    { separator: true },
    { label: 'Open Link', icon: ExternalLink },
    { label: 'Print', icon: Print },
    { label: 'Inspect', icon: QuestionCircle }
]);
<\/script>
```

## Template

ContextMenu offers item customization with the item template that receives the menuitem instance from the model as a parameter.

```vue
<template>
    <div class="flex md:justify-center">
        <ul class="m-0 list-none border border-surface-200 dark:border-surface-700 rounded-sm p-3 flex flex-col gap-2 w-full md:w-120">
            <li
                v-for="product in products"
                :key="product.id"
                :class="['p-2 hover:bg-surface-100 dark:hover:bg-surface-800 rounded-sm border border-transparent transition-all transition-duration-200', { 'border-primary': selectedId === product.id }]"
                @contextmenu="onRightClick($event, product.id)"
            >
                <div class="flex flex-wrap p-2 items-center gap-4">
                    <img class="w-16 shrink-0 rounded-sm" :src="'https://primefaces.org/cdn/primevue/images/product/' + product.image" :alt="product.name" />
                    <div class="flex-1 flex flex-col gap-1">
                        <span class="font-bold text-sm">{{ product.name }}</span>
                        <div class="flex items-center gap-2">
                            <TagIcon class="text-sm" />
                            <span class="text-sm">{{ product.category }}</span>
                        </div>
                    </div>
                    <span class="font-bold ml-8 text-sm">\${{ product.price }}</span>
                </div>
            </li>
        </ul>
        <ContextMenu ref="menu" :model="items" @hide="selectedId = null">
            <template #item="{ item, icon, props }">
                <a v-ripple class="flex items-center px-3 py-2 cursor-pointer" v-bind="props.action">
                    <component :is="icon" />
                    <span class="text-sm ms-2">{{ item.label }}</span>
                    <Badge v-if="item.badge" class="ms-auto" :value="item.badge" />
                    <span v-if="item.shortcut" class="ms-auto border border-surface rounded-sm bg-emphasis text-muted-color text-xs p-1">{{ item.shortcut }}</span>
                    <AngleRight v-if="item.items" class="ms-auto rotate-90 lg:rotate-0" />
                </a>
            </template>
        </ContextMenu>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService'
import AngleRight from '@primeicons/vue/angle-right';
import Instagram from '@primeicons/vue/instagram';
import ShareAlt from '@primeicons/vue/share-alt';
import ShoppingCart from '@primeicons/vue/shopping-cart';
import Star from '@primeicons/vue/star';
import TagIcon from '@primeicons/vue/tag';
import Whatsapp from '@primeicons/vue/whatsapp';

const menu = ref();
const items = ref([
    {
        label: 'Favorite',
        icon: Star,
        shortcut: '⌘+D'
    },
    {
        label: 'Add',
        icon: ShoppingCart,
        shortcut: '⌘+A'
    },
    {
        separator: true
    },
    {
        label: 'Share',
        icon: ShareAlt,
        items: [
            {
                label: 'Whatsapp',
                icon: Whatsapp,
                badge: 2
            },
            {
                label: 'Instagram',
                icon: Instagram,
                badge: 3
            }
        ]
    }
]);

const products = ref(null);
const selectedId = ref(null);

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data));
});

const onRightClick = (event, id) => {
    selectedId.value = id;
    menu.value.show(event);
};

<\/script>
```

## Command

The function to invoke when an item is clicked is defined using the command property.

```vue
<template>
    <Toast />
    <div class="flex sm:justify-center">
        <ul class="m-0 list-none border border-surface rounded-sm p-4 flex flex-col gap-2 w-full sm:w-96">
            <li
                v-for="user in users"
                :key="user.id"
                :class="['p-2 hover:bg-emphasis rounded-sm border border-transparent transition-all duration-200 flex items-center justify-content-between', { 'border-primary!': selectedUser?.id === user.id }]"
                @contextmenu="onRightClick($event, user)"
            >
                <div class="flex flex-1 items-center gap-2">
                    <img :alt="user.name" :src="\`https://primefaces.org/cdn/primevue/images/avatar/\${user.image}\`" class="w-8 h-8" />
                    <span class="font-bold text-sm">{{ user.name }}</span>
                </div>
                <Tag :value="user.role" :severity="getBadge(user)" />
            </li>
        </ul>
        <ContextMenu ref="menu" :model="items" @hide="selectedUser = null" />
    </div>
</template>

<script setup>
import { ref } from 'vue';
import UserPlus from '@primeicons/vue/user-plus';
import Users from '@primeicons/vue/users';
import { useToast } from "primevue/usetoast";

const toast = useToast();
const selectedUser = ref();
const menu = ref();
const users = ref([
    { id: 0, name: 'Amy Elsner', image: 'amyelsner.png', role: 'Admin' },
    { id: 1, name: 'Anna Fali', image: 'annafali.png', role: 'Member' },
    { id: 2, name: 'Asiya Javayant', image: 'asiyajavayant.png', role: 'Member' },
    { id: 3, name: 'Bernardo Dominic', image: 'bernardodominic.png', role: 'Guest' },
    { id: 4, name: 'Elwin Sharvill', image: 'elwinsharvill.png', role: 'Member' }
]);
const items = ref([
    {
        label: 'Roles',
        icon: Users,
        items: [
            {
                label: 'Admin',
                command: () => {
                    selectedUser.value.role = 'Admin';
                }
            },
            {
                label: 'Member',
                command: () => {
                    selectedUser.value.role = 'Member';
                }
            },
            {
                label: 'Guest',
                command: () => {
                    selectedUser.value.role = 'Guest';
                }
            }
        ]
    },
    {
        label: 'Invite',
        icon: UserPlus,
        command: () => {
            toast.add({ severity: 'success', summary: 'Success', detail: 'Invitation sent!', life: 3000 });
        }
    }
]);

const onRightClick = (event, user) => {
    selectedUser.value = user;
    menu.value.show(event);
};

const getBadge = (user) => {
    if (user.role === 'Member') return 'info';
    else if (user.role === 'Guest') return 'warn';
    else return null;
}
<\/script>
```

## Router

Menu items support navigation via router-link, programmatic routing using commands, or external URLs.

```vue
<template>
    <div class="flex justify-center">
        <span class="inline-flex items-center justify-center border-2 border-primary rounded-sm w-16 h-16" @contextmenu="onRightClick" aria-haspopup="true">
            <svg width="35" height="40" viewBox="0 0 35 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                    d="M25.87 18.05L23.16 17.45L25.27 20.46V29.78L32.49 23.76V13.53L29.18 14.73L25.87 18.04V18.05ZM25.27 35.49L29.18 31.58V27.67L25.27 30.98V35.49ZM20.16 17.14H20.03H20.17H20.16ZM30.1 5.19L34.89 4.81L33.08 12.33L24.1 15.67L30.08 5.2L30.1 5.19ZM5.72 14.74L2.41 13.54V23.77L9.63 29.79V20.47L11.74 17.46L9.03 18.06L5.72 14.75V14.74ZM9.63 30.98L5.72 27.67V31.58L9.63 35.49V30.98ZM4.8 5.2L10.78 15.67L1.81 12.33L0 4.81L4.79 5.19L4.8 5.2ZM24.37 21.05V34.59L22.56 37.29L20.46 39.4H14.44L12.34 37.29L10.53 34.59V21.05L12.42 18.23L17.45 26.8L22.48 18.23L24.37 21.05ZM22.85 0L22.57 0.69L17.45 13.08L12.33 0.69L12.05 0H22.85Z"
                    fill="var(--p-primary-color)"
                />
                <path
                    d="M30.69 4.21L24.37 4.81L22.57 0.69L22.86 0H26.48L30.69 4.21ZM23.75 5.67L22.66 3.08L18.05 14.24V17.14H19.7H20.03H20.16H20.2L24.1 15.7L30.11 5.19L23.75 5.67ZM4.21002 4.21L10.53 4.81L12.33 0.69L12.05 0H8.43002L4.22002 4.21H4.21002ZM21.9 17.4L20.6 18.2H14.3L13 17.4L12.4 18.2L12.42 18.23L17.45 26.8L22.48 18.23L22.5 18.2L21.9 17.4ZM4.79002 5.19L10.8 15.7L14.7 17.14H14.74H15.2H16.85V14.24L12.24 3.09L11.15 5.68L4.79002 5.2V5.19Z"
                    fill="var(--p-text-color)"
                />
            </svg>
        </span>
        <ContextMenu ref="routemenu" :model="items">
            <template #item="{ item, icon, props }">
                <router-link v-if="item.route" v-slot="{ href, navigate }" :to="item.route" custom>
                    <a v-ripple :href="href" v-bind="props.action" @click="navigate">
                        <component :is="icon" />
                        <span class="text-sm ml-2">{{ item.label }}</span>
                    </a>
                </router-link>
                <a v-else v-ripple :href="item.url" :target="item.target" v-bind="props.action">
                    <component :is="icon" />
                    <span class="text-sm ml-2">{{ item.label }}</span>
                </a>
            </template>
        </ContextMenu>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import Home from '@primeicons/vue/home';
import Link from '@primeicons/vue/link';
import Palette from '@primeicons/vue/palette';

const router = useRouter();

const routemenu = ref();
const items = ref([
    {
        label: 'Router Link',
        icon: Palette,
        route: '/theming/unstyled'
    },
    {
        label: 'Programmatic',
        icon: Link,
        command: () => {
            router.push('/introduction');
        }
    },
    {
        label: 'External',
        icon: Home,
        url: 'https://vuejs.org/'
    }
]);

const onRightClick = (event) => {
    routemenu.value.show(event);
};
<\/script>
```

## Table

DataTable has built-in support for ContextMenu, see the ContextMenu demo for an example.

## Accessibility

Screen Reader ContextMenu component uses the menubar role with aria-orientation set to "vertical" and the value to describe the menu can either be provided with aria-labelledby or aria-label props. Each list item has a presentation role whereas anchor elements have a menuitem role with aria-label referring to the label of the item and aria-disabled defined if the item is disabled. A submenu within a ContextMenu uses the menu role with an aria-labelledby defined as the id of the submenu root menuitem label. In addition, menuitems that open a submenu have aria-haspopup , aria-expanded and aria-controls to define the relation between the item and the submenu. Keyboard Support Key Function tab When focus is in the menu, closes the context menu and moves focus to the next focusable element in the page sequence. enter If menuitem has a submenu, toggles the visibility of the submenu otherwise activates the menuitem and closes all open overlays. space If menuitem has a submenu, toggles the visibility of the submenu otherwise activates the menuitem and closes all open overlays. escape Closes the context menu. down arrow If focus is not inside the menu and menu is open, add focus to the first item. If an item is already focused, moves focus to the next menuitem within the submenu. up arrow If focus is not inside the menu and menu is open, add focus to the last item. If an item is already focused, moves focus to the next menuitem within the submenu. right arrow Opens a submenu if there is one available and moves focus to the first item. left arrow Closes a submenu and moves focus to the root item of the closed submenu. home Moves focus to the first menuitem within the submenu. end Moves focus to the last menuitem within the submenu.

## Context Menu API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| model | MenuItem[] | - | An array of menuitems. |
| breakpoint | string | 960px | The breakpoint to define the maximum width boundary. |
| global | boolean | false | Attaches the menu to document instead of a particular item. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the overlay gets attached. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| tabindex | string \| number | - | Index of the element in tabbing order. |
| ariaLabel | string | - | Defines a string value that labels an interactive element. |
| ariaLabelledby | string | - | Identifier of the underlying menu element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ContextMenuPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| rootList | ContextMenuPassThroughOptionType | Used to pass attributes to the root list's DOM element. |
| item | ContextMenuPassThroughOptionType | Used to pass attributes to the item's DOM element. |
| itemContent | ContextMenuPassThroughOptionType | Used to pass attributes to the item content's DOM element. |
| itemLink | ContextMenuPassThroughOptionType | Used to pass attributes to the item link's DOM element. |
| itemIcon | ContextMenuPassThroughOptionType | Used to pass attributes to the item icon's DOM element. |
| itemLabel | ContextMenuPassThroughOptionType | Used to pass attributes to the item label's DOM element. |
| submenuIcon | ContextMenuPassThroughOptionType | Used to pass attributes to the submenu icon's DOM element. |
| separator | ContextMenuPassThroughOptionType | Used to pass attributes to the separator's DOM element. |
| submenu | ContextMenuPassThroughOptionType | Used to pass attributes to the submenu's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | ContextMenuPassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-contextmenu | Class name of the root element |
| p-contextmenu-root-list | Class name of the root list element |
| p-contextmenu-item | Class name of the item element |
| p-contextmenu-item-content | Class name of the item content element |
| p-contextmenu-item-link | Class name of the item link element |
| p-contextmenu-item-icon | Class name of the item icon element |
| p-contextmenu-item-label | Class name of the item label element |
| p-contextmenu-submenu-icon | Class name of the submenu icon element |
| p-contextmenu-submenu | Class name of the submenu element |
| p-contextmenu-separator | Class name of the separator element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| contextmenu.background | --p-contextmenu-background | Background of root |
| contextmenu.border.color | --p-contextmenu-border-color | Border color of root |
| contextmenu.color | --p-contextmenu-color | Color of root |
| contextmenu.border.radius | --p-contextmenu-border-radius | Border radius of root |
| contextmenu.shadow | --p-contextmenu-shadow | Shadow of root |
| contextmenu.transition.duration | --p-contextmenu-transition-duration | Transition duration of root |
| contextmenu.list.padding | --p-contextmenu-list-padding | Padding of list |
| contextmenu.list.gap | --p-contextmenu-list-gap | Gap of list |
| contextmenu.item.focus.background | --p-contextmenu-item-focus-background | Focus background of item |
| contextmenu.item.active.background | --p-contextmenu-item-active-background | Active background of item |
| contextmenu.item.color | --p-contextmenu-item-color | Color of item |
| contextmenu.item.focus.color | --p-contextmenu-item-focus-color | Focus color of item |
| contextmenu.item.active.color | --p-contextmenu-item-active-color | Active color of item |
| contextmenu.item.padding | --p-contextmenu-item-padding | Padding of item |
| contextmenu.item.border.radius | --p-contextmenu-item-border-radius | Border radius of item |
| contextmenu.item.gap | --p-contextmenu-item-gap | Gap of item |
| contextmenu.item.icon.color | --p-contextmenu-item-icon-color | Icon color of item |
| contextmenu.item.icon.focus.color | --p-contextmenu-item-icon-focus-color | Icon focus color of item |
| contextmenu.item.icon.active.color | --p-contextmenu-item-icon-active-color | Icon active color of item |
| contextmenu.item.icon.size | --p-contextmenu-item-icon-size | Icon size of item |
| contextmenu.item.label.font.weight | --p-contextmenu-item-label-font-weight | Font weight of item label |
| contextmenu.item.label.font.size | --p-contextmenu-item-label-font-size | Font size of item label |
| contextmenu.submenu.mobile.indent | --p-contextmenu-submenu-mobile-indent | Mobile indent of submenu |
| contextmenu.submenu.label.padding | --p-contextmenu-submenu-label-padding | Padding of submenu label |
| contextmenu.submenu.label.font.weight | --p-contextmenu-submenu-label-font-weight | Font weight of submenu label |
| contextmenu.submenu.label.font.size | --p-contextmenu-submenu-label-font-size | Font size of submenu label |
| contextmenu.submenu.label.background | --p-contextmenu-submenu-label-background | Background of submenu label |
| contextmenu.submenu.label.color | --p-contextmenu-submenu-label-color | Color of submenu label |
| contextmenu.submenu.icon.size | --p-contextmenu-submenu-icon-size | Size of submenu icon |
| contextmenu.submenu.icon.color | --p-contextmenu-submenu-icon-color | Color of submenu icon |
| contextmenu.submenu.icon.focus.color | --p-contextmenu-submenu-icon-focus-color | Focus color of submenu icon |
| contextmenu.submenu.icon.active.color | --p-contextmenu-submenu-icon-active-color | Active color of submenu icon |
| contextmenu.separator.border.color | --p-contextmenu-separator-border-color | Border color of separator |

## Menu Item API
