# Menu

Menu is a navigation / command component that supports dynamic and static positioning.

## Basic

Items are grouped with the items property where each group displays a label header, while a flat separator entry divides the sections.

```vue
<template>
    <div class="flex justify-center">
        <Menu ref="menu" :model="items" popup class="w-40" />
        <Button variant="outlined" severity="secondary" @click="toggle">Account</Button>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const menu = ref();
const items = ref([
    {
        label: 'My Account',
        items: [{ label: 'Profile' }, { label: 'Billing' }, { label: 'Settings' }]
    },
    { separator: true },
    {
        label: 'Security',
        items: [{ label: 'Change Password' }, { label: 'Two-Factor Auth' }]
    },
    { separator: true },
    { label: 'Invite Members' },
    { label: 'Support' },
    { separator: true },
    { label: 'Sign out' }
]);

const toggle = (event) => {
    menu.value.toggle(event);
};
<\/script>
```

## Group

Items are organized into labeled groups separated by a separator . Checkbox and radio selections are driven from the model by toggling an item's icon through its command .

```vue
<template>
    <div class="flex justify-center">
        <Menu :model="items" class="w-60" />
    </div>
</template>

<script setup>
import Blank from '@primeicons/vue/blank';
import Check from '@primeicons/vue/check';
import Dot from '@primeicons/vue/dot';
import { computed, ref } from 'vue';

const notifications = ref(true);
const sound = ref(false);
const marketing = ref(false);
const autoUpdate = ref(true);
const theme = ref('light');
const language = ref('en');

const items = computed(() => [
    {
        label: 'Notifications',
        items: [
            {
                label: 'Enable notifications',
                icon: this.notifications ? Check : Blank,
                command: () => (this.notifications = !this.notifications)
            },
            {
                label: 'Play sound',
                icon: this.sound ? Check : Blank,
                command: () => (this.sound = !this.sound)
            },
            {
                label: 'Marketing emails',
                icon: this.marketing ? Check : Blank,
                command: () => (this.marketing = !this.marketing)
            }
        ]
    },
    { separator: true },
    {
        label: 'System',
        items: [
            {
                label: 'Auto-update apps',
                icon: this.autoUpdate ? Check : Blank,
                command: () => (this.autoUpdate = !this.autoUpdate)
            }
        ]
    },
    { separator: true },
    {
        label: 'Appearance',
        items: [
            {
                label: 'Light',
                icon: this.theme === 'light' ? Dot : Blank,
                command: () => (this.theme = 'light')
            },
            {
                label: 'Dark',
                icon: this.theme === 'dark' ? Dot : Blank,
                command: () => (this.theme = 'dark')
            },
            {
                label: 'System',
                icon: this.theme === 'system' ? Dot : Blank,
                command: () => (this.theme = 'system')
            }
        ]
    },
    { separator: true },
    {
        label: 'Language',
        items: [
            {
                label: 'English',
                icon: this.language === 'en' ? Dot : Blank,
                command: () => (this.language = 'en')
            },
            {
                label: 'Türkçe',
                icon: this.language === 'tr' ? Dot : Blank,
                command: () => (this.language = 'tr')
            },
            {
                label: 'Deutsch',
                icon: this.language === 'de' ? Dot : Blank,
                command: () => (this.language = 'de')
            }
        ]
    }
]);
<\/script>
```

## Toggleable

Nested submenus are toggleable by default. Use toggleable to override the default per item (e.g. force a top-level group to be toggleable, or keep a nested group always open) and expandedKeys to control open/closed state.

```vue
<template>
    <div class="flex justify-center">
        <Menu :model="items" class="w-44" />
    </div>
</template>

<script setup>
import Cloud from '@primeicons/vue/cloud';
import Copy from '@primeicons/vue/copy';
import Download from '@primeicons/vue/download';
import Facebook from '@primeicons/vue/facebook';
import File from '@primeicons/vue/file';
import FileEdit from '@primeicons/vue/file-edit';
import FileExport from '@primeicons/vue/file-export';
import Globe from '@primeicons/vue/globe';
import Link from '@primeicons/vue/link';
import Linkedin from '@primeicons/vue/linkedin';
import Pencil from '@primeicons/vue/pencil';
import Send from '@primeicons/vue/send';
import ShareAlt from '@primeicons/vue/share-alt';
import Twitter from '@primeicons/vue/twitter';
import { ref } from 'vue';

const items = ref([
    {
        label: 'Document',
        items: [
            { label: 'New file', icon: File },
            { label: 'Open recent', icon: FileEdit },
            { label: 'Duplicate', icon: Copy },
            {
                label: 'Import',
                icon: Download,
                items: [
                    { label: 'From file', icon: File },
                    { label: 'From cloud', icon: Cloud },
                    { label: 'From URL', icon: Globe }
                ]
            },
            {
                label: 'Export',
                icon: FileExport,
                items: [
                    { label: 'PDF' },
                    { label: 'Word' },
                    { label: 'Markdown' },
                    { label: 'HTML' },
                    {
                        label: 'More',
                        items: [{ label: 'EPUB' }, { label: 'RTF' }, { label: 'LaTeX' }, { label: 'Plain Text' }]
                    }
                ]
            },
            {
                label: 'Share',
                icon: ShareAlt,
                items: [
                    { label: 'Send via email', icon: Send },
                    { label: 'Copy link', icon: Link },
                    { separator: true },
                    {
                        label: 'Social',
                        toggleable: false,
                        items: [
                            { label: 'Twitter', icon: Twitter },
                            { label: 'Facebook', icon: Facebook },
                            { label: 'LinkedIn', icon: Linkedin }
                        ]
                    }
                ]
            },
            { label: 'Rename', icon: Pencil }
        ]
    }
]);
<\/script>
```

## Popup

Popup mode is enabled by setting the popup property to true and calling the toggle method to display the menu relative to its target.

```vue
<template>
    <div class="flex justify-center">
        <Menu ref="menu" :model="items" popup />
        <Button type="button" severity="secondary" variant="outlined" iconOnly aria-label="Apps" @click="toggle">
            <Bars />
        </Button>
    </div>
</template>

<script setup>
import Bars from '@primeicons/vue/bars';
import Copy from '@primeicons/vue/copy';
import Download from '@primeicons/vue/download';
import File from '@primeicons/vue/file';
import FileEdit from '@primeicons/vue/file-edit';
import FileExport from '@primeicons/vue/file-export';
import Pencil from '@primeicons/vue/pencil';
import ShareAlt from '@primeicons/vue/share-alt';
import { ref } from 'vue';

const menu = ref();
const items = ref([
    {
        label: 'Document',
        items: [
            { label: 'New file', icon: File },
            { label: 'Open recent', icon: FileEdit },
            { label: 'Duplicate', icon: Copy },
            { label: 'Import', icon: Download },
            { label: 'Export', icon: FileExport },
            { label: 'Share', icon: ShareAlt },
            { label: 'Rename', icon: Pencil }
        ]
    }
]);

const toggle = (event) => {
    menu.value.toggle(event);
};
<\/script>
```

## Template

Menu offers item customization with the item template that receives the menuitem instance from the model as a parameter. The submenu label has its own submenulabel template, additional slots named start and end are provided to embed content before or after the menu.

```vue
<template>
    <div class="flex justify-center">
        <Menu :model="items" class="w-full md:w-60">
            <template #start>
                <span class="inline-flex items-center gap-1 px-1.5 py-1.5">
                    <svg width="35" height="40" viewBox="0 0 35 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="h-8">
                        <path
                            d="M25.87 18.05L23.16 17.45L25.27 20.46V29.78L32.49 23.76V13.53L29.18 14.73L25.87 18.04V18.05ZM25.27 35.49L29.18 31.58V27.67L25.27 30.98V35.49ZM20.16 17.14H20.03H20.17H20.16ZM30.1 5.19L34.89 4.81L33.08 12.33L24.1 15.67L30.08 5.2L30.1 5.19ZM5.72 14.74L2.41 13.54V23.77L9.63 29.79V20.47L11.74 17.46L9.03 18.06L5.72 14.75V14.74ZM9.63 30.98L5.72 27.67V31.58L9.63 35.49V30.98ZM4.8 5.2L10.78 15.67L1.81 12.33L0 4.81L4.79 5.19L4.8 5.2ZM24.37 21.05V34.59L22.56 37.29L20.46 39.4H14.44L12.34 37.29L10.53 34.59V21.05L12.42 18.23L17.45 26.8L22.48 18.23L24.37 21.05ZM22.85 0L22.57 0.69L17.45 13.08L12.33 0.69L12.05 0H22.85Z"
                            fill="var(--p-primary-color)"
                        />
                        <path
                            d="M30.69 4.21L24.37 4.81L22.57 0.69L22.86 0H26.48L30.69 4.21ZM23.75 5.67L22.66 3.08L18.05 14.24V17.14H19.7H20.03H20.16H20.2L24.1 15.7L30.11 5.19L23.75 5.67ZM4.21002 4.21L10.53 4.81L12.33 0.69L12.05 0H8.43002L4.22002 4.21H4.21002ZM21.9 17.4L20.6 18.2H14.3L13 17.4L12.4 18.2L12.42 18.23L17.45 26.8L22.48 18.23L22.5 18.2L21.9 17.4ZM4.79002 5.19L10.8 15.7L14.7 17.14H14.74H15.2H16.85V14.24L12.24 3.09L11.15 5.68L4.79002 5.2V5.19Z"
                            fill="var(--p-text-color)"
                        />
                    </svg>
                    <span class="text-lg font-semibold">PRIME<span class="text-primary">APP</span></span>
                </span>
            </template>
            <template #submenulabel="{ item }">
                <span class="text-primary font-bold text-sm">{{ item.label }}</span>
            </template>
            <template #item="{ item, icon, label, props }">
                <a v-ripple class="flex items-center px-2.5 py-1.5 cursor-pointer" :class="item.linkClass" v-bind="props.action">
                    <component :is="icon" />
                    <span class="ms-2 text-sm">{{ label }}</span>
                    <Badge v-if="item.badge" class="ms-auto" :value="item.badge" />
                    <span v-if="item.shortcut" class="ms-auto border border-surface rounded-sm bg-emphasis text-muted-color text-xs px-1 py-0.5">{{ item.shortcut }}</span>
                </a>
            </template>
            <template #end>
                <button v-ripple class="relative overflow-hidden w-full border-0 bg-transparent flex items-start p-1.5 pl-3.5 hover:bg-surface-100 dark:hover:bg-surface-800 rounded-none cursor-pointer transition-colors duration-200">
                    <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" class="mr-2" shape="circle" />
                    <span class="inline-flex flex-col items-start">
                        <span class="text-sm font-bold">Amy Elsner</span>
                        <span class="text-xs">Admin</span>
                    </span>
                </button>
            </template>
        </Menu>
    </div>
</template>

<script setup>
import Cog from '@primeicons/vue/cog';
import Inbox from '@primeicons/vue/inbox';
import Plus from '@primeicons/vue/plus';
import Search from '@primeicons/vue/search';
import SignOut from '@primeicons/vue/sign-out';
import { ref } from "vue";

const items = ref([
    {
        separator: true
    },
    {
        label: 'Documents',
        items: [
            {
                label: 'New',
                icon: Plus,
                shortcut: '⌘+N'
            },
            {
                label: 'Search',
                icon: Search,
                shortcut: '⌘+S'
            }
        ]
    },
    {
        label: 'Profile',
        items: [
            {
                label: 'Settings',
                icon: Cog,
                shortcut: '⌘+O'
            },
            {
                label: 'Messages',
                icon: Inbox,
                badge: 2
            },
            {
                label: 'Logout',
                icon: SignOut,
                shortcut: '⌘+Q',
                linkClass: 'text-red-500! dark:text-red-400!'
            }
        ]
    },
    {
        separator: true
    }
]);
<\/script>
```

## Command

The function to invoke when an item is clicked is defined using the command property.

```vue
<template>
    <div class="flex justify-center">
        <Menu :model="items" />
        <Toast />
    </div>
</template>

<script setup>
import Plus from '@primeicons/vue/plus';
import Search from '@primeicons/vue/search';
import { ref } from "vue";
import { useToast } from "primevue/usetoast";

const toast = useToast();

const items = ref([
    {
        label: 'New',
        icon: Plus,
        command: () => {
            toast.add({ severity: 'success', summary: 'Success', detail: 'File created', life: 3000 });
        }
    },
    {
        label: 'Search',
        icon: Search,
        command: () => {
            toast.add({ severity: 'warn', summary: 'Search Completed', detail: 'No results found', life: 3000 });
        }
    }
]);
<\/script>
```

## Router

Menu items support navigation via router-link, programmatic routing using commands, or external URLs.

```vue
<template>
    <div class="flex justify-center">
        <Menu :model="items">
            <template #item="{ item, icon, label, props }">
                <router-link v-if="item.route" v-slot="{ href, navigate }" :to="item.route" custom>
                    <a v-ripple :href="href" v-bind="props.action" @click="navigate">
                        <component :is="icon" />
                        <span class="text-sm ml-2">{{ label }}</span>
                    </a>
                </router-link>
                <a v-else v-ripple :href="item.url" :target="item.target" v-bind="props.action">
                    <component :is="icon" />
                    <span class="text-sm ml-2">{{ label }}</span>
                </a>
            </template>
        </Menu>
    </div>
</template>

<script setup>
import Home from '@primeicons/vue/home';
import Link from '@primeicons/vue/link';
import Palette from '@primeicons/vue/palette';
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const items = ref([
    {
        label: 'Navigate',
        items: [
            { label: 'Router Link', icon: Palette, route: '/theming' },
            {
                label: 'Programmatic',
                icon: Link,
                command: () => {
                    router.push('/installation');
                }
            },
            { label: 'External', icon: Home, url: 'https://vuejs.org/', target: '_blank' }
        ]
    }
]);
<\/script>
```

## Controlled

Menu state can be controlled programmatically with the expandedKeys property that defines the keys of the toggleable submenus that are expanded. This property is an object whose key matches an item's key field and value is a boolean. Note that expandedKeys also supports two-way binding with the v-model directive.

```vue
<template>
    <div>
        <div class="flex flex-wrap gap-2 mb-6">
            <Button type="button" severity="secondary" variant="outlined" size="small" @click="expandAll">
                <Plus />
                Expand All
            </Button>
            <Button type="button" severity="secondary" variant="outlined" size="small" @click="collapseAll">
                <Minus />
                Collapse All
            </Button>
        </div>
        <Menu v-model:expandedKeys="expandedKeys" :model="items" />
    </div>
</template>

<script setup>
import Briefcase from '@primeicons/vue/briefcase';
import Calendar from '@primeicons/vue/calendar';
import ChartBar from '@primeicons/vue/chart-bar';
import CheckCircle from '@primeicons/vue/check-circle';
import File from '@primeicons/vue/file';
import Folder from '@primeicons/vue/folder';
import Home from '@primeicons/vue/home';
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';
import { ref } from 'vue';

const expandedKeys = ref({ reports: true });
const items = ref([
    { key: 'dashboard', label: 'Dashboard', icon: Home },
    { separator: true },
    {
        key: 'workspace',
        label: 'Workspace',
        items: [
            {
                key: 'projects',
                label: 'Projects',
                icon: Folder,
                items: [
                    { key: 'projects-active', label: 'Active', icon: Briefcase },
                    { key: 'projects-completed', label: 'Completed', icon: CheckCircle }
                ]
            },
            {
                key: 'reports',
                label: 'Reports',
                icon: File,
                items: [
                    { key: 'reports-monthly', label: 'Monthly', icon: Calendar },
                    { key: 'reports-yearly', label: 'Yearly', icon: ChartBar }
                ]
            }
        ]
    }
]);

const expandNodes = (nodes, keys) => {
    for (const item of nodes || []) {
        if (item.items && item.key) {
            keys[item.key] = true;
            expandNodes(item.items, keys);
        }
    }
};

const expandAll = () => {
    const keys = {};

    expandNodes(items.value, keys);
    expandedKeys.value = keys;
};

const collapseAll = () => {
    expandedKeys.value = {};
};
<\/script>
```

## Accessibility

Screen Reader Menu component uses the menu role and the value to describe the menu can either be provided with aria-labelledby or aria-label props. Each list item has a presentation role whereas anchor elements have a menuitem role with aria-label referring to the label of the item and aria-disabled defined if the item is disabled. A submenu within a Menu uses the group role with an aria-labelledby defined as the id of the submenu root menuitem label. In popup mode, the component implicitly manages the aria-expanded , aria-haspopup and aria-controls attributes of the target element to define the relation between the target and the popup. Keyboard Support Key Function tab Add focus to the first item if focus moves in to the menu. If the focus is already within the menu, focus moves to the next focusable item in the page tab sequence. shift + tab Add focus to the last item if focus moves in to the menu. If the focus is already within the menu, focus moves to the previous focusable item in the page tab sequence. enter Activates the focused menuitem. If menu is in overlay mode, popup gets closes and focus moves to target. space Activates the focused menuitem. If menu is in overlay mode, popup gets closes and focus moves to target. escape If menu is in overlay mode, popup gets closes and focus moves to target. down arrow Moves focus to the next menuitem. up arrow Moves focus to the previous menuitem. home Moves focus to the first menuitem. end Moves focus to the last menuitem.

## Menu API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| model | MenuItem[] | - | An array of menuitems. |
| expandedKeys | MenuExpandedKeys | - | When provided, switches the component to controlled mode; each key is the DOM id of a toggleable submenu header and the value its expansion flag. Pair with  `@update:expandedKeys`  or  `v-model:expandedKeys` . |
| popup | boolean | false | Defines if menu would displayed as a popup. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the overlay gets attached. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| tabindex | string \| number | - | Index of the element in tabbing order. |
| ariaLabel | string | - | Defines a string value that labels an interactive element. |
| ariaLabelledby | string | - | Identifier of the underlying input element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | MenuPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| list | MenuPassThroughOptionType | Used to pass attributes to the list's DOM element. |
| submenuLabel | MenuPassThroughOptionType | Used to pass attributes to the submenu label's DOM element (non-toggleable group headers). |
| submenuList | MenuPassThroughOptionType | Used to pass attributes to the nested submenu list's DOM element. |
| item | MenuPassThroughOptionType | Used to pass attributes to the item's DOM element. |
| itemContent | MenuPassThroughOptionType | Used to pass attributes to the item content's DOM element. |
| itemLink | MenuPassThroughOptionType | Used to pass attributes to the item link's DOM element. |
| itemIcon | MenuPassThroughOptionType | Used to pass attributes to the item icon's DOM element. |
| itemLabel | MenuPassThroughOptionType | Used to pass attributes to the item label's DOM element. |
| itemSubmenuIcon | MenuPassThroughOptionType | Used to pass attributes to the item submenu toggle icon's DOM element (toggleable items). |
| separator | MenuPassThroughOptionType | Used to pass attributes to the separator's DOM element. |
| start | MenuPassThroughOptionType | Used to pass attributes to the start of the component. |
| end | MenuPassThroughOptionType | Used to pass attributes to the end of the component. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | MenuPassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-menu | Class name of the root element |
| p-menu-start | Class name of the start element |
| p-menu-list | Class name of the list element |
| p-menu-submenu-label | Class name of the submenu label element (non-toggleable group headers). |
| p-menu-submenu-list | Class name of the nested submenu list element. |
| p-menu-separator | Class name of the separator element |
| p-menu-end | Class name of the end element |
| p-menu-item | Class name of the item element |
| p-menu-item-content | Class name of the item content element |
| p-menu-item-link | Class name of the item link element |
| p-menu-item-icon | Class name of the item icon element |
| p-menu-item-label | Class name of the item label element |
| p-menu-item-submenu-icon | Class name of the item submenu toggle icon element (toggleable items). |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| menu.background | --p-menu-background | Background of root |
| menu.border.color | --p-menu-border-color | Border color of root |
| menu.color | --p-menu-color | Color of root |
| menu.border.radius | --p-menu-border-radius | Border radius of root |
| menu.shadow | --p-menu-shadow | Shadow of root |
| menu.transition.duration | --p-menu-transition-duration | Transition duration of root |
| menu.list.padding | --p-menu-list-padding | Padding of list |
| menu.list.gap | --p-menu-list-gap | Gap of list |
| menu.item.focus.background | --p-menu-item-focus-background | Focus background of item |
| menu.item.color | --p-menu-item-color | Color of item |
| menu.item.focus.color | --p-menu-item-focus-color | Focus color of item |
| menu.item.padding | --p-menu-item-padding | Padding of item |
| menu.item.border.radius | --p-menu-item-border-radius | Border radius of item |
| menu.item.gap | --p-menu-item-gap | Gap of item |
| menu.item.icon.color | --p-menu-item-icon-color | Icon color of item |
| menu.item.icon.focus.color | --p-menu-item-icon-focus-color | Icon focus color of item |
| menu.item.icon.size | --p-menu-item-icon-size | Icon size of item |
| menu.item.label.font.weight | --p-menu-item-label-font-weight | Font weight of item label |
| menu.item.label.font.size | --p-menu-item-label-font-size | Font size of item label |
| menu.submenu.label.padding | --p-menu-submenu-label-padding | Padding of submenu label |
| menu.submenu.label.font.weight | --p-menu-submenu-label-font-weight | Font weight of submenu label |
| menu.submenu.label.font.size | --p-menu-submenu-label-font-size | Font size of submenu label |
| menu.submenu.label.background | --p-menu-submenu-label-background | Background of submenu label |
| menu.submenu.label.color | --p-menu-submenu-label-color | Color of submenu label |
| menu.submenu.icon.size | --p-menu-submenu-icon-size | Size of submenu icon |
| menu.submenu.icon.color | --p-menu-submenu-icon-color | Color of submenu icon |
| menu.submenu.icon.focus.color | --p-menu-submenu-icon-focus-color | Focus color of submenu icon |
| menu.separator.border.color | --p-menu-separator-border-color | Border color of separator |

## Menu Item API
