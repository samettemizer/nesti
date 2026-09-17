# Dock

Dock is a navigation component consisting of menuitems.

## Basic

Dock requires a collection of menuitems as its model . Default location is bottom and other sides are also available when defined with the position property. Content of the dock component is defined by item template.

```vue
<template>
    <div class="dock-demo">
        <div class="flex flex-wrap gap-4 mb-7">
            <div v-for="pos of positions" :key="pos.value" class="flex items-center">
                <RadioButton v-model="position" :value="pos.value" :inputId="pos.label" name="dock" />
                <label :for="pos.label" class="ml-2 text-sm"> {{ pos.label }} </label>
            </div>
        </div>
        <div class="dock-window">
            <Dock :model="items" :position="position">
                <template #itemicon="{ item }">
                    <img v-tooltip.top="item.label" :alt="item.label" :src="item.icon" style="width: 100%" />
                </template>
            </Dock>
        </div>
    </div>
</template>

<script setup>
import { ref } from "vue";

const items = ref([
    {
        label: 'Finder',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/finder.svg'
    },
    {
        label: 'App Store',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/appstore.svg'
    },
    {
        label: 'Photos',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/photos.svg'
    },
    {
        label: 'Trash',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/trash.png'
    }
]);
const position = ref('bottom');
const positions = ref([
    {
        label: 'Bottom',
        value: 'bottom'
    },
    {
        label: 'Top',
        value: 'top'
    },
    {
        label: 'Left',
        value: 'left'
    },
    {
        label: 'Right',
        value: 'right'
    }
]);
<\/script>

<style scoped>
.dock-demo > .dock-window {
    width: 100%;
    height: 450px;
    position: relative;
    background-image: url("https://primefaces.org/cdn/primevue/images/dock/window.jpg");
    background-repeat: no-repeat;
    background-size: cover;
    z-index: 1;
}

.dock-demo > .p-dock {
    z-index: 1000;
}
</style>
```

## Advanced

A mock desktop UI implemented with various components in addition to Dock.

```vue
<template>
    <div class="dock-demo">
        <Toast position="top-center" group="tc" />

        <Menubar :model="menubarItems">
            <template #start>
                <Apple class="mx-2" />
            </template>
            <template #end>
                <div class="flex items-center">
                    <Video class="mx-2" />
                    <Wifi class="mx-2" />
                    <VolumeUp class="mx-2" />
                    <span class="px-2 text-sm">Fri 13:07</span>
                    <Search class="mx-2" />
                    <Bars class="mx-2" />
                </div>
            </template>
        </Menubar>

        <div class="dock-window dock-advanced">
            <Dock :model="items" position="bottom">
                <template #item="{ item }">
                    <a v-tooltip.top="item.label" href="#" class="p-dock-item-link" @click="onDockItemClick($event, item)">
                        <img :alt="item.label" :src="item.icon" style="width: 100%" />
                    </a>
                </template>
            </Dock>

            <Dialog v-model:visible="displayFinder" header="Finder" :breakpoints="{ '960px': '50vw' }" :style="{ width: '40vw' }" :maximizable="true">
                <Tree :value="nodes" />
            </Dialog>

            <Dialog v-model:visible="displayTerminal" header="Terminal" :breakpoints="{ '960px': '50vw' }" :style="{ width: '40vw' }" :maximizable="true">
                <Terminal welcomeMessage="Welcome to PrimeVue(cmd: 'date', 'greet {0}' and 'random')" prompt="primevue $" />
            </Dialog>

            <Galleria v-model:visible="displayPhotos" :value="images" :responsiveOptions="responsiveOptions" :numVisible="2" containerStyle="width: 400px" :circular="true" :fullScreen="true" :showThumbnails="false" :showItemNavigators="true">
                <template #item="slotProps">
                    <img :src="slotProps.item.itemImageSrc" :alt="slotProps.item.alt" style="width: 100%" />
                </template>
            </Galleria>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useToast } from 'primevue/usetoast';
import TerminalService from 'primevue/terminalservice';
import { NodeService } from '@/service/NodeService';
import { PhotoService } from '@/service/PhotoService';
import AlignCenter from '@primeicons/vue/align-center';
import AlignJustify from '@primeicons/vue/align-justify';
import AlignLeft from '@primeicons/vue/align-left';
import AlignRight from '@primeicons/vue/align-right';
import Apple from '@primeicons/vue/apple';
import Bars from '@primeicons/vue/bars';
import Bookmark from '@primeicons/vue/bookmark';
import CalendarMinus from '@primeicons/vue/calendar-minus';
import CalendarPlus from '@primeicons/vue/calendar-plus';
import CalendarTimes from '@primeicons/vue/calendar-times';
import ExternalLink from '@primeicons/vue/external-link';
import Filter from '@primeicons/vue/filter';
import Pencil from '@primeicons/vue/pencil';
import Plus from '@primeicons/vue/plus';
import Print from '@primeicons/vue/print';
import Search from '@primeicons/vue/search';
import Trash from '@primeicons/vue/trash';
import UserMinus from '@primeicons/vue/user-minus';
import UserPlus from '@primeicons/vue/user-plus';
import Users from '@primeicons/vue/users';
import Video from '@primeicons/vue/video';
import VolumeUp from '@primeicons/vue/volume-up';
import Wifi from '@primeicons/vue/wifi';

onMounted(() => {
    PhotoService.getImages().then(data => images.value = data);
    NodeService.getTreeNodes().then(data => nodes.value = data);
    TerminalService.on('command', commandHandler);
})

onBeforeUnmount(() => {
    TerminalService.off('command', commandHandler);
})

const displayFinder = ref(false);
const displayTerminal = ref(false);
const displayPhotos = ref(false);
const images = ref();
const nodes = ref();
const toast = useToast();
const items = ref([
    {
        label: 'Finder',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/finder.svg',
        command: () => {
            displayFinder.value = true;
        }
    },
    {
        label: 'Terminal',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/terminal.svg',
        command: () => {
            displayTerminal.value = true;
        }
    },
    {
        label: 'App Store',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/appstore.svg',
        url: 'https://www.apple.com/app-store/'
    },
    {
        label: 'Safari',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/safari.svg',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Safari has stopped working', group: 'tc', life: 3000 });
        }
    },
    {
        label: 'Photos',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/photos.svg',
        command: () => {
            displayPhotos.value = true;
        }
    },
    {
        label: 'GitHub',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/github.svg',
        url: 'https://github.com/primefaces/primevue'
    },
    {
        label: 'Trash',
        icon: 'https://primefaces.org/cdn/primevue/images/dock/trash.png',
        command: () => {
            toast.add({ severity: 'info', summary: 'Trash is empty', life: 3000 });
        }
    }
]);
const menubarItems = ref([
    {
        label: 'Finder',
        class: 'menubar-root'
    },
    {
        label: 'File',
        items: [
            {
                label: 'New',
                icon: Plus,
                items: [
                    {
                        label: 'Bookmark',
                        icon: Bookmark
                    },
                    {
                        label: 'Video',
                        icon: Video
                    }
                ]
            },
            {
                label: 'Delete',
                icon: Trash
            },
            {
                separator: true
            },
            {
                label: 'Export',
                icon: ExternalLink
            }
        ]
    },
    {
        label: 'Edit',
        items: [
            {
                label: 'Left',
                icon: AlignLeft
            },
            {
                label: 'Right',
                icon: AlignRight
            },
            {
                label: 'Center',
                icon: AlignCenter
            },
            {
                label: 'Justify',
                icon: AlignJustify
            }
        ]
    },
    {
        label: 'Users',
        items: [
            {
                label: 'New',
                icon: UserPlus
            },
            {
                label: 'Delete',
                icon: UserMinus
            },
            {
                label: 'Search',
                icon: Users,
                items: [
                    {
                        label: 'Filter',
                        icon: Filter,
                        items: [
                            {
                                label: 'Print',
                                icon: Print
                            }
                        ]
                    },
                    {
                        icon: Bars,
                        label: 'List'
                    }
                ]
            }
        ]
    },
    {
        label: 'Events',
        items: [
            {
                label: 'Edit',
                icon: Pencil,
                items: [
                    {
                        label: 'Save',
                        icon: CalendarPlus
                    },
                    {
                        label: 'Delete',
                        icon: CalendarMinus
                    }
                ]
            },
            {
                label: 'Archieve',
                icon: CalendarTimes,
                items: [
                    {
                        label: 'Remove',
                        icon: CalendarMinus
                    }
                ]
            }
        ]
    },
    {
        label: 'Quit'
    }
]);
const responsiveOptions = ref([
    {
        breakpoint: '1024px',
        numVisible: 3
    },
    {
        breakpoint: '768px',
        numVisible: 2
    },
    {
        breakpoint: '560px',
        numVisible: 1
    }
]);

const onDockItemClick = (event, item) => {
    if (item.command) {
        item.command();
    }

    event.preventDefault();
};

const commandHandler = (text) => {
    let response;
    let argsIndex = text.indexOf(' ');
    let command = argsIndex !== -1 ? text.substring(0, argsIndex) : text;

    switch(command) {
        case "date":
            response = 'Today is ' + new Date().toDateString();
            break;

        case "greet":
            response = 'Hola ' + text.substring(argsIndex + 1) + '!';
            break;

        case "random":
            response = Math.floor(Math.random() * 100);
            break;

        default:
            response = "Unknown command: " + command;
    }

    TerminalService.emit('response', response);
};
<\/script>

<style scoped>
.dock-demo > .dock-window {
    width: 100%;
    height: 450px;
    position: relative;
    background-image: url("https://primefaces.org/cdn/primevue/images/dock/window.jpg");
    background-repeat: no-repeat;
    background-size: cover;
}

.dock-demo .p-menubar {
    padding: 0;
    border-radius: 0;
}
</style>
```

## Accessibility

Screen Reader Dock component uses the menu role with the aria-orientation and the value to describe the menu can either be provided with aria-labelledby or aria-label props. Each list item has a presentation role whereas anchor elements have a menuitem role with aria-label referring to the label of the item and aria-disabled defined if the item is disabled. Keyboard Support Key Function tab Add focus to the first item if focus moves in to the menu. If the focus is already within the menu, focus moves to the next focusable item in the page tab sequence. shift + tab Add focus to the last item if focus moves in to the menu. If the focus is already within the menu, focus moves to the previous focusable item in the page tab sequence. enter Activates the focused menuitem. space Activates the focused menuitem. down arrow Moves focus to the next menuitem in vertical layout. up arrow Moves focus to the previous menuitem in vertical layout. home Moves focus to the first menuitem in horizontal layout. end Moves focus to the last menuitem in horizontal layout.

## Dock API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| model | MenuItem[] | - | MenuModel instance to define the action items. |
| position | any | bottom | Position of element. |
| class | any | - | Style class of the element. |
| style | any | - | Inline style of the element. |
| breakpoint | string | 960px | The breakpoint to define the maximum width boundary. |
| tooltipOptions | DockTooltipOptions | - | Whether to display the tooltip on items. The modifiers of Tooltip can be used like an object in it. Valid keys are 'event' and 'position'. |
| menuId | string | - | Unique identifier of the menu. |
| tabindex | string \| number | - | Index of the element in tabbing order. |
| ariaLabelledby | string | - | Establishes relationships between the component and label(s) where its value should be one or more element IDs. |
| ariaLabel | string | - | Establishes a string value that labels the component. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | DockPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| listContainer | DockPassThroughOptionType | Used to pass attributes to the list container's DOM element. |
| list | DockPassThroughOptionType | Used to pass attributes to the list's DOM element. |
| item | DockPassThroughOptionType | Used to pass attributes to the  item's DOM element. |
| itemContent | DockPassThroughOptionType | Used to pass attributes to the item content's DOM element. |
| itemLink | DockPassThroughOptionType | Used to pass attributes to the item link's DOM element. |
| itemIcon | DockPassThroughOptionType | Used to pass attributes to the item icon's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-dock | Class name of the root element |
| p-dock-list-container | Class name of the list container element |
| p-dock-list | Class name of the list element |
| p-dock-item | Class name of the item element |
| p-dock-item-content | Class name of the item content element |
| p-dock-item-link | Class name of the item link element |
| p-dock-item-icon | Class name of the item icon element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| dock.background | --p-dock-background | Background of root |
| dock.border.color | --p-dock-border-color | Border color of root |
| dock.padding | --p-dock-padding | Padding of root |
| dock.border.radius | --p-dock-border-radius | Border radius of root |
| dock.item.border.radius | --p-dock-item-border-radius | Border radius of item |
| dock.item.padding | --p-dock-item-padding | Padding of item |
| dock.item.size | --p-dock-item-size | Size of item |
| dock.item.focus.ring.width | --p-dock-item-focus-ring-width | Focus ring width of item |
| dock.item.focus.ring.style | --p-dock-item-focus-ring-style | Focus ring style of item |
| dock.item.focus.ring.color | --p-dock-item-focus-ring-color | Focus ring color of item |
| dock.item.focus.ring.offset | --p-dock-item-focus-ring-offset | Focus ring offset of item |
| dock.item.focus.ring.shadow | --p-dock-item-focus-ring-shadow | Focus ring shadow of item |

## Menu Item API
