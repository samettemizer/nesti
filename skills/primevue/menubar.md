# Menubar

Menubar is a horizontal menu component.

## Basic

Menubar requires nested menuitems as its model .

```vue
<template>
    <div class="flex justify-center">
        <Menubar :model="items" />
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Clipboard from '@primeicons/vue/clipboard';
import Copy from '@primeicons/vue/copy';
import Download from '@primeicons/vue/download';
import File from '@primeicons/vue/file';
import FolderOpen from '@primeicons/vue/folder-open';
import Replay from '@primeicons/vue/replay';
import Save from '@primeicons/vue/save';
import Undo from '@primeicons/vue/undo';

const items = ref([
    {
        label: 'File',
        items: [{ label: 'New Document', icon: File }, { label: 'Open', icon: FolderOpen }, { separator: true }, { label: 'Save', icon: Save }, { label: 'Save As…', icon: Download }]
    },
    {
        label: 'Edit',
        items: [{ label: 'Undo', icon: Undo }, { label: 'Redo', icon: Replay }, { separator: true }, { label: 'Cut', icon: Clipboard }, { label: 'Copy', icon: Copy }, { label: 'Paste', icon: File }]
    },
    {
        label: 'View',
        items: [{ label: 'Zoom In' }, { label: 'Zoom Out' }, { label: 'Reset Zoom' }, { separator: true }, { label: 'Full Screen' }]
    },
    {
        label: 'Help',
        items: [{ label: 'Documentation' }, { label: 'Support' }, { separator: true }, { label: 'About' }]
    }
]);
<\/script>
```

## Submenus

Menuitems with nested items create cascading submenus.

```vue
<template>
    <div class="flex justify-center">
        <Menubar :model="items" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const items = ref([
    {
        label: 'File',
        items: [
            { label: 'New File' },
            { label: 'Open File…' },
            {
                label: 'Open Recent',
                items: [
                    { label: 'todo.md' },
                    { label: 'changelog.md' },
                    { label: 'readme.md' },
                    {
                        label: 'Older',
                        items: [{ label: 'release-notes.md' }, { label: 'roadmap.md' }, { label: 'contributing.md' }, { label: 'license.txt' }]
                    },
                    { separator: true },
                    { label: 'Clear Recent' }
                ]
            },
            { separator: true },
            { label: 'Save' },
            { label: 'Save As…' }
        ]
    },
    {
        label: 'View',
        items: [{ label: 'Reload' }, { label: 'Force Reload' }, { separator: true }, { label: 'Toggle DevTools' }]
    }
]);
<\/script>
```

## Template

Menubar offers item customization with the item template that receives the menuitem instance from the model as a parameter. Additional slots named start and end are provided to embed content before or after the menu.

```vue
<template>
    <div>
        <Menubar :model="items">
            <template #start>
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
            </template>
            <template #item="{ item, props, hasSubmenu, root }">
                <a v-ripple class="flex items-center px-3 py-2 cursor-pointer gap-2" v-bind="props.action">
                    <span class="text-sm">{{ item.label }}</span>
                    <Badge v-if="item.badge" :class="root ? '' : 'ms-auto'" :value="item.badge" />
                    <span v-if="item.shortcut" class="ms-auto border border-surface rounded-sm bg-emphasis text-muted-color text-xs p-1">{{ item.shortcut }}</span>
                    <component :is="root ? 'AngleDown' : 'AngleRight'" v-if="hasSubmenu" class="ms-auto" />
                </a>
            </template>
            <template #end>
                <div class="flex items-center gap-2">
                    <InputText placeholder="Search" type="text" class="w-36" />
                    <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
                </div>
            </template>
        </Menubar>
    </div>
</template>

<script setup>
import { ref } from "vue";
import AngleDown from '@primeicons/vue/angle-down';
import AngleRight from '@primeicons/vue/angle-right';
import Bolt from '@primeicons/vue/bolt';
import Home from '@primeicons/vue/home';
import Pencil from '@primeicons/vue/pencil';
import Search from '@primeicons/vue/search';
import Server from '@primeicons/vue/server';

const items = ref([
    {
        label: 'Home',
        icon: Home
    },
    {
        label: 'Projects',
        icon: Search,
        badge: 3,
        items: [
            {
                label: 'Core',
                icon: Bolt,
                shortcut: '⌘+S'
            },
            {
                label: 'Blocks',
                icon: Server,
                shortcut: '⌘+B'
            },
            {
                separator: true
            },
            {
                label: 'UI Kit',
                icon: Pencil,
                shortcut: '⌘+U'
            }
        ]
    }
]);
<\/script>
```

## Command

The command property defines the callback to run when an item is activated by click or a key event.

```vue
<template>
    <div>
        <Menubar :model="items" />
        <Toast />
    </div>
</template>

<script setup>
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import Cloud from '@primeicons/vue/cloud';
import CloudDownload from '@primeicons/vue/cloud-download';
import CloudUpload from '@primeicons/vue/cloud-upload';
import File from '@primeicons/vue/file';
import Plus from '@primeicons/vue/plus';
import Print from '@primeicons/vue/print';
import Search from '@primeicons/vue/search';

const toast = useToast();

const items = ref([
    {
        label: 'File',
        icon: File,
        items: [
            {
                label: 'New',
                icon: Plus,
                command: () => {
                    toast.add({ severity: 'success', summary: 'Success', detail: 'File created', life: 3000 });
                }
            },
            {
                label: 'Print',
                icon: Print,
                command: () => {
                    toast.add({ severity: 'error', summary: 'Error', detail: 'No printer connected', life: 3000 });
                }
            }
        ]
    },
    {
        label: 'Search',
        icon: Search,
        command: () => {
            toast.add({ severity: 'warn', summary: 'Search Results', detail: 'No results found', life: 3000 });
        }
    },
    {
        separator: true
    },
    {
        label: 'Sync',
        icon: Cloud,
        items: [
            {
                label: 'Import',
                icon: CloudDownload,
                command: () => {
                    toast.add({ severity: 'info', summary: 'Downloads', detail: 'Downloaded from cloud', life: 3000 });
                }
            },
            {
                label: 'Export',
                icon: CloudUpload,
                command: () => {
                    toast.add({ severity: 'info', summary: 'Shared', detail: 'Exported to cloud', life: 3000 });
                }
            }
        ]
    }
]);
<\/script>
```

## Router

Menu items support navigation via router-link, programmatic routing using commands, or external URLs.

```vue
<template>
    <div>
        <Menubar :model="items">
            <template #item="{ item, icon, label, props, hasSubmenu }">
                <router-link v-if="item.route" v-slot="{ href, navigate }" :to="item.route" custom>
                    <a v-ripple :href="href" v-bind="props.action" @click="navigate">
                        <component :is="icon" />
                        <span class="text-sm">{{ label }}</span>
                    </a>
                </router-link>
                <a v-else v-ripple :href="item.url" :target="item.target" v-bind="props.action">
                    <component :is="icon" />
                    <span class="text-sm">{{ label }}</span>
                    <AngleDown v-if="hasSubmenu" />
                </a>
            </template>
        </Menubar>
    </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from 'vue-router';
import AngleDown from '@primeicons/vue/angle-down';
import Home from '@primeicons/vue/home';
import Link from '@primeicons/vue/link';
import Palette from '@primeicons/vue/palette';

const router = useRouter();

const items = ref([
    {
        label: 'Router',
        icon: Palette,
        items: [
            {
                label: 'Installation',
                route: '/installation'
            },
            {
                label: 'Configuration',
                route: '/configuration'
            }
        ]
    },
    {
        label: 'Programmatic',
        icon: Link,
        command: () => {
            router.push('/installation');
        }
    },
    {
        label: 'External',
        icon: Home,
        items: [
            {
                label: 'Vue.js',
                url: 'https://vuejs.org/'
            },
            {
                label: 'Vite.js',
                url: 'https://vitejs.dev/'
            }
        ]
    }
]);
<\/script>
```

## Advanced

Menubar is a simple horizontal navigation component, for advanced use cases consider Marketing and Application NavBars in PrimeBlocks or templates with horizontal menus in application templates.

## Accessibility

Screen Reader Menubar component uses the menubar role and the value to describe the menu can either be provided with aria-labelledby or aria-label props. Each list item has a menuitem role with aria-label referring to the label of the item and aria-disabled defined if the item is disabled. A submenu within a MenuBar uses the menu role with an aria-labelledby defined as the id of the submenu root menuitem label. In addition, menuitems that open a submenu have aria-haspopup , aria-expanded and aria-controls to define the relation between the item and the submenu. In mobile viewports, a menu icon appears with a button role along with aria-haspopup , aria-expanded and aria-controls to manage the relation between the overlay menubar and the button. The value to describe the button can be defined aria-label or aria-labelledby specified using buttonProps , by default navigation key of the aria property from the locale API as the aria-label . Keyboard Support Key Function tab Add focus to the first item if focus moves in to the menu. If the focus is already within the menu, focus moves to the next focusable item in the page tab sequence. shift + tab Add focus to the first item if focus moves in to the menu. If the focus is already within the menu, focus moves to the previous focusable item in the page tab sequence. enter If menuitem has a submenu, toggles the visibility of the submenu otherwise activates the menuitem and closes all open overlays. space If menuitem has a submenu, toggles the visibility of the submenu otherwise activates the menuitem and closes all open overlays. escape If focus is inside a popup submenu, closes the submenu and moves focus to the root item of the closed submenu. down arrow If focus is on a root element, open a submenu and moves focus to the first element in the submenu otherwise moves focus to the next menuitem within the submenu. up arrow If focus is on a root element, opens a submenu and moves focus to the last element in the submenu otherwise moves focus to the previous menuitem within the submenu. right arrow If focus is on a root element, moves focus to the next menuitem otherwise opens a submenu if there is one available and moves focus to the first item. left arrow If focus is on a root element, moves focus to the previous menuitem otherwise closes a submenu and moves focus to the root item of the closed submenu. home Moves focus to the first menuitem within the submenu. end Moves focus to the last menuitem within the submenu. any printable character Moves focus to the menuitem whose label starts with the characters being typed.

## Menubar API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| model | MenuItem[] | - | An array of menuitems. |
| breakpoint | string | 960px | The breakpoint to define the maximum width boundary. |
| buttonProps | ButtonHTMLAttributes | - | Used to pass all properties of the HTMLButtonElement to the menu button. |
| ariaLabel | string | - | Defines a string value that labels an interactive element. |
| ariaLabelledby | string | - | Identifier of the underlying input element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | MenubarPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| rootList | MenubarPassThroughOptionType | Used to pass attributes to the root list's DOM element. |
| item | MenubarPassThroughOptionType | Used to pass attributes to the item's DOM element. |
| itemContent | MenubarPassThroughOptionType | Used to pass attributes to the item content's DOM element. |
| itemLink | MenubarPassThroughOptionType | Used to pass attributes to the item link's DOM element. |
| itemIcon | MenubarPassThroughOptionType | Used to pass attributes to the item icon's DOM element. |
| itemLabel | MenubarPassThroughOptionType | Used to pass attributes to the item label's DOM element. |
| submenuIcon | MenubarPassThroughOptionType | Used to pass attributes to the submenu icon's DOM element. |
| separator | MenubarPassThroughOptionType | Used to pass attributes to the separator's DOM element. |
| button | MenubarPassThroughOptionType | Used to pass attributes to the mobile menu button's DOM element. |
| buttonIcon | MenubarPassThroughOptionType | Used to pass attributes to the mobile menu button icon's DOM element. |
| submenu | MenubarPassThroughOptionType | Used to pass attributes to the submenu's DOM element. |
| start | MenubarPassThroughOptionType | Used to pass attributes to the start of the component. |
| end | MenubarPassThroughOptionType | Used to pass attributes to the end of the component. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-menubar | Class name of the root element |
| p-menubar-start | Class name of the start element |
| p-menubar-button | Class name of the button element |
| p-menubar-root-list | Class name of the root list element |
| p-menubar-item | Class name of the item element |
| p-menubar-item-content | Class name of the item content element |
| p-menubar-item-link | Class name of the item link element |
| p-menubar-item-icon | Class name of the item icon element |
| p-menubar-item-label | Class name of the item label element |
| p-menubar-submenu-icon | Class name of the submenu icon element |
| p-menubar-submenu | Class name of the submenu element |
| p-menubar-separator | Class name of the separator element |
| p-menubar-end | Class name of the end element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| menubar.background | --p-menubar-background | Background of root |
| menubar.border.color | --p-menubar-border-color | Border color of root |
| menubar.border.radius | --p-menubar-border-radius | Border radius of root |
| menubar.color | --p-menubar-color | Color of root |
| menubar.gap | --p-menubar-gap | Gap of root |
| menubar.padding | --p-menubar-padding | Padding of root |
| menubar.transition.duration | --p-menubar-transition-duration | Transition duration of root |
| menubar.base.item.border.radius | --p-menubar-base-item-border-radius | Border radius of base item |
| menubar.base.item.padding | --p-menubar-base-item-padding | Padding of base item |
| menubar.item.focus.background | --p-menubar-item-focus-background | Focus background of item |
| menubar.item.active.background | --p-menubar-item-active-background | Active background of item |
| menubar.item.color | --p-menubar-item-color | Color of item |
| menubar.item.focus.color | --p-menubar-item-focus-color | Focus color of item |
| menubar.item.active.color | --p-menubar-item-active-color | Active color of item |
| menubar.item.padding | --p-menubar-item-padding | Padding of item |
| menubar.item.border.radius | --p-menubar-item-border-radius | Border radius of item |
| menubar.item.gap | --p-menubar-item-gap | Gap of item |
| menubar.item.icon.color | --p-menubar-item-icon-color | Icon color of item |
| menubar.item.icon.focus.color | --p-menubar-item-icon-focus-color | Icon focus color of item |
| menubar.item.icon.active.color | --p-menubar-item-icon-active-color | Icon active color of item |
| menubar.item.icon.size | --p-menubar-item-icon-size | Icon size of item |
| menubar.item.label.font.weight | --p-menubar-item-label-font-weight | Font weight of item label |
| menubar.item.label.font.size | --p-menubar-item-label-font-size | Font size of item label |
| menubar.submenu.padding | --p-menubar-submenu-padding | Padding of submenu |
| menubar.submenu.gap | --p-menubar-submenu-gap | Gap of submenu |
| menubar.submenu.background | --p-menubar-submenu-background | Background of submenu |
| menubar.submenu.border.color | --p-menubar-submenu-border-color | Border color of submenu |
| menubar.submenu.border.radius | --p-menubar-submenu-border-radius | Border radius of submenu |
| menubar.submenu.shadow | --p-menubar-submenu-shadow | Shadow of submenu |
| menubar.submenu.mobile.indent | --p-menubar-submenu-mobile-indent | Mobile indent of submenu |
| menubar.submenu.icon.size | --p-menubar-submenu-icon-size | Icon size of submenu |
| menubar.submenu.icon.color | --p-menubar-submenu-icon-color | Icon color of submenu |
| menubar.submenu.icon.focus.color | --p-menubar-submenu-icon-focus-color | Icon focus color of submenu |
| menubar.submenu.icon.active.color | --p-menubar-submenu-icon-active-color | Icon active color of submenu |
| menubar.separator.border.color | --p-menubar-separator-border-color | Border color of separator |
| menubar.mobile.button.border.radius | --p-menubar-mobile-button-border-radius | Border radius of mobile button |
| menubar.mobile.button.size | --p-menubar-mobile-button-size | Size of mobile button |
| menubar.mobile.button.color | --p-menubar-mobile-button-color | Color of mobile button |
| menubar.mobile.button.hover.color | --p-menubar-mobile-button-hover-color | Hover color of mobile button |
| menubar.mobile.button.hover.background | --p-menubar-mobile-button-hover-background | Hover background of mobile button |
| menubar.mobile.button.focus.ring.width | --p-menubar-mobile-button-focus-ring-width | Focus ring width of mobile button |
| menubar.mobile.button.focus.ring.style | --p-menubar-mobile-button-focus-ring-style | Focus ring style of mobile button |
| menubar.mobile.button.focus.ring.color | --p-menubar-mobile-button-focus-ring-color | Focus ring color of mobile button |
| menubar.mobile.button.focus.ring.offset | --p-menubar-mobile-button-focus-ring-offset | Focus ring offset of mobile button |
| menubar.mobile.button.focus.ring.shadow | --p-menubar-mobile-button-focus-ring-shadow | Focus ring shadow of mobile button |

## Menu Item API
