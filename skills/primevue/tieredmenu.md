# TieredMenu

TieredMenu displays submenus in nested overlays.

## Basic

TieredMenu requires a collection of menuitems as its model .

```vue
<template>
    <div class="flex justify-center">
        <TieredMenu :model="items" />
    </div>
</template>

<script setup>
import { ref } from "vue";
import Copy from '@primeicons/vue/copy';
import File from '@primeicons/vue/file';
import FileEdit from '@primeicons/vue/file-edit';
import FolderOpen from '@primeicons/vue/folder-open';
import Image from '@primeicons/vue/image';
import Plus from '@primeicons/vue/plus';
import Print from '@primeicons/vue/print';
import Search from '@primeicons/vue/search';
import ShareAlt from '@primeicons/vue/share-alt';
import Slack from '@primeicons/vue/slack';
import Times from '@primeicons/vue/times';
import Video from '@primeicons/vue/video';
import Whatsapp from '@primeicons/vue/whatsapp';

const items = ref([
    {
        label: 'File',
        icon: File,
        items: [
            {
                label: 'New',
                icon: Plus,
                items: [
                    {
                        label: 'Document',
                        icon: File
                    },
                    {
                        label: 'Image',
                        icon: Image
                    },
                    {
                        label: 'Video',
                        icon: Video
                    }
                ]
            },
            {
                label: 'Open',
                icon: FolderOpen
            },
            {
                label: 'Print',
                icon: Print
            }
        ]
    },
    {
        label: 'Edit',
        icon: FileEdit,
        items: [
            {
                label: 'Copy',
                icon: Copy
            },
            {
                label: 'Delete',
                icon: Times
            }
        ]
    },
    {
        label: 'Search',
        icon: Search
    },
    {
        separator: true
    },
    {
        label: 'Share',
        icon: ShareAlt,
        items: [
            {
                label: 'Slack',
                icon: Slack
            },
            {
                label: 'Whatsapp',
                icon: Whatsapp
            }
        ]
    }
]);
<\/script>
```

## Popup

Popup mode is enabled by adding popup property and calling toggle method with an event of the target.

```vue
<template>
    <div class="flex justify-center">
        <Button type="button" @click="toggle" aria-haspopup="true" aria-controls="overlay_tmenu">Toggle</Button>
        <TieredMenu ref="menu" id="overlay_tmenu" :model="items" popup />
    </div>
</template>

<script setup>
import { ref } from "vue";
import Copy from '@primeicons/vue/copy';
import File from '@primeicons/vue/file';
import FileEdit from '@primeicons/vue/file-edit';
import FolderOpen from '@primeicons/vue/folder-open';
import Image from '@primeicons/vue/image';
import Plus from '@primeicons/vue/plus';
import Print from '@primeicons/vue/print';
import Search from '@primeicons/vue/search';
import ShareAlt from '@primeicons/vue/share-alt';
import Slack from '@primeicons/vue/slack';
import Times from '@primeicons/vue/times';
import Video from '@primeicons/vue/video';
import Whatsapp from '@primeicons/vue/whatsapp';

const menu = ref();
const items = ref([
    {
        label: 'File',
        icon: File,
        items: [
            {
                label: 'New',
                icon: Plus,
                items: [
                    {
                        label: 'Document',
                        icon: File
                    },
                    {
                        label: 'Image',
                        icon: Image
                    },
                    {
                        label: 'Video',
                        icon: Video
                    }
                ]
            },
            {
                label: 'Open',
                icon: FolderOpen
            },
            {
                label: 'Print',
                icon: Print
            }
        ]
    },
    {
        label: 'Edit',
        icon: FileEdit,
        items: [
            {
                label: 'Copy',
                icon: Copy
            },
            {
                label: 'Delete',
                icon: Times
            }
        ]
    },
    {
        label: 'Search',
        icon: Search
    },
    {
        separator: true
    },
    {
        label: 'Share',
        icon: ShareAlt,
        items: [
            {
                label: 'Slack',
                icon: Slack
            },
            {
                label: 'Whatsapp',
                icon: Whatsapp
            }
        ]
    }
]);

const toggle = (event) => {
    menu.value.toggle(event);
};
<\/script>
```

## Template

TieredMenu offers item customization with the item template that receives the menuitem instance from the model as a parameter.

```vue
<template>
    <div class="flex justify-center">
        <TieredMenu :model="items">
            <template #item="{ item, icon, props, hasSubmenu }">
                <a v-ripple class="flex items-center px-3 py-2 cursor-pointer" v-bind="props.action">
                    <component :is="icon" />
                    <span class="ms-2 text-sm">{{ item.label }}</span>
                    <Badge v-if="item.badge" class="ml-auto" :value="item.badge" />
                    <span v-if="item.shortcut" class="ml-auto border border-surface rounded-sm bg-emphasis text-muted-color text-xs p-1">{{ item.shortcut }}</span>
                    <AngleRight v-if="hasSubmenu" class="ms-auto" />
                </a>
            </template>
        </TieredMenu>
    </div>
</template>

<script setup>
import AngleRight from '@primeicons/vue/angle-right';
import { ref } from "vue";
import Copy from '@primeicons/vue/copy';
import File from '@primeicons/vue/file';
import FileEdit from '@primeicons/vue/file-edit';
import FolderOpen from '@primeicons/vue/folder-open';
import Image from '@primeicons/vue/image';
import Plus from '@primeicons/vue/plus';
import Print from '@primeicons/vue/print';
import Search from '@primeicons/vue/search';
import ShareAlt from '@primeicons/vue/share-alt';
import Slack from '@primeicons/vue/slack';
import Times from '@primeicons/vue/times';
import Video from '@primeicons/vue/video';
import Whatsapp from '@primeicons/vue/whatsapp';

const items = ref([
    {
        label: 'File',
        icon: File,
        items: [
            {
                label: 'New',
                icon: Plus,
                items: [
                    {
                        label: 'Docs',
                        icon: File,
                        shortcut: '⌘+N'
                    },
                    {
                        label: 'Image',
                        icon: Image,
                        shortcut: '⌘+I'
                    },
                    {
                        label: 'Video',
                        icon: Video,
                        shortcut: '⌘+L'
                    }
                ]
            },
            {
                label: 'Open',
                icon: FolderOpen,
                shortcut: '⌘+O'
            },
            {
                label: 'Print',
                icon: Print,
                shortcut: '⌘+P'
            }
        ]
    },
    {
        label: 'Edit',
        icon: FileEdit,
        items: [
            {
                label: 'Copy',
                icon: Copy,
                shortcut: '⌘+C'
            },
            {
                label: 'Delete',
                icon: Times,
                shortcut: '⌘+D'
            }
        ]
    },
    {
        label: 'Search',
        icon: Search,
        shortcut: '⌘+S'
    },
    {
        separator: true
    },
    {
        label: 'Share',
        icon: ShareAlt,
        items: [
            {
                label: 'Slack',
                icon: Slack,
                badge: 2
            },
            {
                label: 'Whatsapp',
                icon: Whatsapp,
                badge: 3
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
    <div class="flex justify-center">
        <TieredMenu :model="items" />
        <Toast />
    </div>
</template>

<script setup>
import { ref } from "vue";
import Cloud from '@primeicons/vue/cloud';
import CloudDownload from '@primeicons/vue/cloud-download';
import CloudUpload from '@primeicons/vue/cloud-upload';
import File from '@primeicons/vue/file';
import Plus from '@primeicons/vue/plus';
import Print from '@primeicons/vue/print';
import Search from '@primeicons/vue/search';
import { useToast } from "primevue/usetoast";

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
    <div class="flex justify-center">
        <TieredMenu :model="items">
            <template #item="{ item, icon, props, hasSubmenu }">
                <router-link v-if="item.route" v-slot="{ href, navigate }" :to="item.route" custom>
                    <a v-ripple :href="href" v-bind="props.action" @click="navigate">
                        <component :is="icon" />
                        <span class="ml-2">{{ item.label }}</span>
                    </a>
                </router-link>
                <a v-else v-ripple :href="item.url" :target="item.target" v-bind="props.action">
                    <component :is="icon" />
                    <span class="ml-2">{{ item.label }}</span>
                    <AngleRight v-if="hasSubmenu" class="ml-auto" />
                </a>
            </template>
        </TieredMenu>
    </div>
</template>

<script setup>
import { ref } from "vue";
import AngleRight from '@primeicons/vue/angle-right';
import Home from '@primeicons/vue/home';
import Link from '@primeicons/vue/link';
import Palette from '@primeicons/vue/palette';
import { useRouter } from 'vue-router';

const router = useRouter();

const items = ref([
    {
        label: 'Router',
        icon: Palette,
        items: [
            {
                label: 'Theming',
                route: '/theming/styled'
            },
            {
                label: 'UI Kit',
                route: '/uikit'
            }
        ]
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
        items: [
            {
                label: 'Vue.js',
                url: 'https://vuejs.org/'
            },
            {
                label: 'Vite.js',
                url: 'https://vite.dev/'
            }
        ]
    }
]);
<\/script>
```

## Accessibility

Screen Reader TieredMenu component uses the menubar role with aria-orientation set to "vertical" and the value to describe the menu can either be provided with aria-labelledby or aria-label props. Each list item has a presentation role whereas anchor elements have a menuitem role with aria-label referring to the label of the item and aria-disabled defined if the item is disabled. A submenu within a TieredMenu uses the menu role with an aria-labelledby defined as the id of the submenu root menuitem label. In addition, menuitems that open a submenu have aria-haspopup , aria-expanded and aria-controls to define the relation between the item and the submenu. In popup mode, the component implicitly manages the aria-expanded , aria-haspopup and aria-controls attributes of the target element to define the relation between the target and the popup. Keyboard Support Key Function tab Add focus to the first item if focus moves in to the menu. If the focus is already within the menu, focus moves to the next focusable item in the page tab sequence. shift + tab Add focus to the last item if focus moves in to the menu. If the focus is already within the menu, focus moves to the previous focusable item in the page tab sequence. enter If menuitem has a submenu, toggles the visibility of the submenu otherwise activates the menuitem and closes all open overlays. space If menuitem has a submenu, toggles the visibility of the submenu otherwise activates the menuitem and closes all open overlays. escape If focus is inside a popup submenu, closes the submenu and moves focus to the root item of the closed submenu. down arrow Moves focus to the next menuitem within the submenu. up arrow Moves focus to the previous menuitem within the submenu. right arrow Opens a submenu if there is one available and moves focus to the first item. left arrow Closes a submenu and moves focus to the root item of the closed submenu. home Moves focus to the first menuitem within the submenu. end Moves focus to the last menuitem within the submenu.

## Tiered Menu API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| model | MenuItem[] | - | An array of menuitems. |
| popup | boolean | false | Defines if menu would displayed as a popup. |
| breakpoint | string | 960px | The breakpoint to define the maximum width boundary. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the overlay gets attached. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
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
| root | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| rootList | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the root list's DOM element. |
| item | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the list item's DOM element. |
| itemContent | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the item content's DOM element. |
| itemLink | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the item link's DOM element. |
| itemIcon | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the item icon's DOM element. |
| itemLabel | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the item label's DOM element. |
| submenuIcon | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the submenu icon's DOM element. |
| separator | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the separator's DOM element. |
| submenu | TieredMenuPassThroughOptionType<T> | Used to pass attributes to the submenu's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | TieredMenuPassThroughTransitionType<any> | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-tieredmenu | Class name of the root element |
| p-tieredmenu-start | Class name of the start element |
| p-tieredmenu-root-list | Class name of the root list element |
| p-tieredmenu-item | Class name of the item element |
| p-tieredmenu-item-content | Class name of the item content element |
| p-tieredmenu-item-link | Class name of the item link element |
| p-tieredmenu-item-icon | Class name of the item icon element |
| p-tieredmenu-item-label | Class name of the item label element |
| p-tieredmenu-submenu-icon | Class name of the submenu icon element |
| p-tieredmenu-submenu | Class name of the submenu element |
| p-tieredmenu-separator | Class name of the separator element |
| p-tieredmenu-end | Class name of the end element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| tieredmenu.background | --p-tieredmenu-background | Background of root |
| tieredmenu.border.color | --p-tieredmenu-border-color | Border color of root |
| tieredmenu.color | --p-tieredmenu-color | Color of root |
| tieredmenu.border.radius | --p-tieredmenu-border-radius | Border radius of root |
| tieredmenu.shadow | --p-tieredmenu-shadow | Shadow of root |
| tieredmenu.transition.duration | --p-tieredmenu-transition-duration | Transition duration of root |
| tieredmenu.list.padding | --p-tieredmenu-list-padding | Padding of list |
| tieredmenu.list.gap | --p-tieredmenu-list-gap | Gap of list |
| tieredmenu.item.focus.background | --p-tieredmenu-item-focus-background | Focus background of item |
| tieredmenu.item.active.background | --p-tieredmenu-item-active-background | Active background of item |
| tieredmenu.item.color | --p-tieredmenu-item-color | Color of item |
| tieredmenu.item.focus.color | --p-tieredmenu-item-focus-color | Focus color of item |
| tieredmenu.item.active.color | --p-tieredmenu-item-active-color | Active color of item |
| tieredmenu.item.padding | --p-tieredmenu-item-padding | Padding of item |
| tieredmenu.item.border.radius | --p-tieredmenu-item-border-radius | Border radius of item |
| tieredmenu.item.gap | --p-tieredmenu-item-gap | Gap of item |
| tieredmenu.item.icon.color | --p-tieredmenu-item-icon-color | Icon color of item |
| tieredmenu.item.icon.focus.color | --p-tieredmenu-item-icon-focus-color | Icon focus color of item |
| tieredmenu.item.icon.active.color | --p-tieredmenu-item-icon-active-color | Icon active color of item |
| tieredmenu.item.icon.size | --p-tieredmenu-item-icon-size | Icon size of item |
| tieredmenu.item.label.font.weight | --p-tieredmenu-item-label-font-weight | Font weight of item label |
| tieredmenu.item.label.font.size | --p-tieredmenu-item-label-font-size | Font size of item label |
| tieredmenu.submenu.mobile.indent | --p-tieredmenu-submenu-mobile-indent | Mobile indent of submenu |
| tieredmenu.submenu.icon.size | --p-tieredmenu-submenu-icon-size | Size of submenu icon |
| tieredmenu.submenu.icon.color | --p-tieredmenu-submenu-icon-color | Color of submenu icon |
| tieredmenu.submenu.icon.focus.color | --p-tieredmenu-submenu-icon-focus-color | Focus color of submenu icon |
| tieredmenu.submenu.icon.active.color | --p-tieredmenu-submenu-icon-active-color | Active color of submenu icon |
| tieredmenu.separator.border.color | --p-tieredmenu-separator-border-color | Border color of separator |

## Menu Item API
