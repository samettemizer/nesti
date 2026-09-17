# MegaMenu

MegaMenu is navigation component that displays submenus together.

## Basic

MegaMenu requires a collection of menuitems as its model .

```vue
<template>
    <MegaMenu :model="items" />
</template>

<script setup>
import { ref } from "vue";
import Box from '@primeicons/vue/box';
import Clock from '@primeicons/vue/clock';
import Mobile from '@primeicons/vue/mobile';

const items = ref([
    {
        label: 'Furniture',
        icon: Box,
        items: [
            [
                {
                    label: 'Living Room',
                    items: [{ label: 'Accessories' }, { label: 'Armchair' }, { label: 'Coffee Table' }, { label: 'Couch' }, { label: 'TV Stand' }]
                }
            ],
            [
                {
                    label: 'Kitchen',
                    items: [{ label: 'Bar stool' }, { label: 'Chair' }, { label: 'Table' }]
                },
                {
                    label: 'Bathroom',
                    items: [{ label: 'Accessories' }]
                }
            ],
            [
                {
                    label: 'Bedroom',
                    items: [{ label: 'Bed' }, { label: 'Chaise lounge' }, { label: 'Cupboard' }, { label: 'Dresser' }, { label: 'Wardrobe' }]
                }
            ],
            [
                {
                    label: 'Office',
                    items: [{ label: 'Bookcase' }, { label: 'Cabinet' }, { label: 'Chair' }, { label: 'Desk' }, { label: 'Executive Chair' }]
                }
            ]
        ]
    },
    {
        label: 'Electronics',
        icon: Mobile,
        items: [
            [
                {
                    label: 'Computer',
                    items: [{ label: 'Monitor' }, { label: 'Mouse' }, { label: 'Notebook' }, { label: 'Keyboard' }, { label: 'Printer' }, { label: 'Storage' }]
                }
            ],
            [
                {
                    label: 'Home Theater',
                    items: [{ label: 'Projector' }, { label: 'Speakers' }, { label: 'TVs' }]
                }
            ],
            [
                {
                    label: 'Gaming',
                    items: [{ label: 'Accessories' }, { label: 'Console' }, { label: 'PC' }, { label: 'Video Games' }]
                }
            ],
            [
                {
                    label: 'Appliances',
                    items: [{ label: 'Coffee Machine' }, { label: 'Fridge' }, { label: 'Oven' }, { label: 'Vaccum Cleaner' }, { label: 'Washing Machine' }]
                }
            ]
        ]
    },
    {
        label: 'Sports',
        icon: Clock,
        items: [
            [
                {
                    label: 'Football',
                    items: [{ label: 'Kits' }, { label: 'Shoes' }, { label: 'Shorts' }, { label: 'Training' }]
                }
            ],
            [
                {
                    label: 'Running',
                    items: [{ label: 'Accessories' }, { label: 'Shoes' }, { label: 'T-Shirts' }, { label: 'Shorts' }]
                }
            ],
            [
                {
                    label: 'Swimming',
                    items: [{ label: 'Kickboard' }, { label: 'Nose Clip' }, { label: 'Swimsuits' }, { label: 'Paddles' }]
                }
            ],
            [
                {
                    label: 'Tennis',
                    items: [{ label: 'Balls' }, { label: 'Rackets' }, { label: 'Shoes' }, { label: 'Training' }]
                }
            ]
        ]
    }
]);
<\/script>
```

## Vertical

Layout of the MegaMenu is changed with the orientation property that accepts horizontal and vertical as options.

```vue
<template>
    <div>
        <MegaMenu :model="items" orientation="vertical" />
    </div>
</template>

<script setup>
import { ref } from "vue";
import Box from '@primeicons/vue/box';
import Clock from '@primeicons/vue/clock';
import Mobile from '@primeicons/vue/mobile';

const items = ref([
    {
        label: 'Furniture',
        icon: Box,
        items: [
            [
                {
                    label: 'Living Room',
                    items: [{ label: 'Accessories' }, { label: 'Armchair' }, { label: 'Coffee Table' }, { label: 'Couch' }, { label: 'TV Stand' }]
                }
            ],
            [
                {
                    label: 'Kitchen',
                    items: [{ label: 'Bar stool' }, { label: 'Chair' }, { label: 'Table' }]
                },
                {
                    label: 'Bathroom',
                    items: [{ label: 'Accessories' }]
                }
            ],
            [
                {
                    label: 'Bedroom',
                    items: [{ label: 'Bed' }, { label: 'Chaise lounge' }, { label: 'Cupboard' }, { label: 'Dresser' }, { label: 'Wardrobe' }]
                }
            ],
            [
                {
                    label: 'Office',
                    items: [{ label: 'Bookcase' }, { label: 'Cabinet' }, { label: 'Chair' }, { label: 'Desk' }, { label: 'Executive Chair' }]
                }
            ]
        ]
    },
    {
        label: 'Electronics',
        icon: Mobile,
        items: [
            [
                {
                    label: 'Computer',
                    items: [{ label: 'Monitor' }, { label: 'Mouse' }, { label: 'Notebook' }, { label: 'Keyboard' }, { label: 'Printer' }, { label: 'Storage' }]
                }
            ],
            [
                {
                    label: 'Home Theater',
                    items: [{ label: 'Projector' }, { label: 'Speakers' }, { label: 'TVs' }]
                }
            ],
            [
                {
                    label: 'Gaming',
                    items: [{ label: 'Accessories' }, { label: 'Console' }, { label: 'PC' }, { label: 'Video Games' }]
                }
            ],
            [
                {
                    label: 'Appliances',
                    items: [{ label: 'Coffee Machine' }, { label: 'Fridge' }, { label: 'Oven' }, { label: 'Vaccum Cleaner' }, { label: 'Washing Machine' }]
                }
            ]
        ]
    },
    {
        label: 'Sports',
        icon: Clock,
        items: [
            [
                {
                    label: 'Football',
                    items: [{ label: 'Kits' }, { label: 'Shoes' }, { label: 'Shorts' }, { label: 'Training' }]
                }
            ],
            [
                {
                    label: 'Running',
                    items: [{ label: 'Accessories' }, { label: 'Shoes' }, { label: 'T-Shirts' }, { label: 'Shorts' }]
                }
            ],
            [
                {
                    label: 'Swimming',
                    items: [{ label: 'Kickboard' }, { label: 'Nose Clip' }, { label: 'Swimsuits' }, { label: 'Paddles' }]
                }
            ],
            [
                {
                    label: 'Tennis',
                    items: [{ label: 'Balls' }, { label: 'Rackets' }, { label: 'Shoes' }, { label: 'Training' }]
                }
            ]
        ]
    }
]);
<\/script>
```

## Template

Custom content can be placed inside the MegaMenu using templating. MegaMenu should be horizontal for custom content.

```vue
<template>
    <div>
        <MegaMenu :model="items" class="p-3 bg-surface-0 dark:bg-surface-900" style="border-radius: 3rem; display: flex">
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
            <template #item="{ item, icon, label }">
                <a v-if="item.root" v-ripple class="flex items-center cursor-pointer px-3 py-2 overflow-hidden relative font-semibold uppercase" style="border-radius: 2rem">
                    <component :is="icon" />
                    <span class="ml-2">{{ label }}</span>
                </a>
                <a v-else-if="!item.image" class="flex items-center p-3 cursor-pointer mb-2 gap-2">
                    <span class="inline-flex items-center justify-center rounded-full bg-primary text-primary-contrast w-12 h-12">
                        <component :is="icon" />
                    </span>
                    <span class="inline-flex flex-col gap-1">
                        <span class="font-medium text-surface-900 dark:text-surface-0">{{ label }}</span>
                        <span class="whitespace-nowrap text-sm">{{ item.subtext }}</span>
                    </span>
                </a>
                <div v-else class="flex flex-col items-start gap-4">
                    <img alt="megamenu-demo" :src="item.image" class="w-full" />
                    <span class="text-sm">{{ item.subtext }}</span>
                    <Button variant="outlined">{{ label }}</Button>
                </div>
            </template>
            <template #end>
                <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
            </template>
        </MegaMenu>
    </div>
</template>

<script setup>
import { ref } from "vue";
import Comments from '@primeicons/vue/comments';
import File from '@primeicons/vue/file';
import Globe from '@primeicons/vue/globe';
import List from '@primeicons/vue/list';
import Question from '@primeicons/vue/question';
import Search from '@primeicons/vue/search';
import Shield from '@primeicons/vue/shield';
import Star from '@primeicons/vue/star';
import Users from '@primeicons/vue/users';

const items = ref([
    {
        label: 'Company',
        root: true,
        items: [
            [
                {
                    items: [
                        { label: 'Features', icon: List, subtext: 'Subtext of item' },
                        { label: 'Customers', icon: Users, subtext: 'Subtext of item' },
                        { label: 'Case Studies', icon: File, subtext: 'Subtext of item' }
                    ]
                }
            ],
            [
                {
                    items: [
                        { label: 'Solutions', icon: Shield, subtext: 'Subtext of item' },
                        { label: 'Faq', icon: Question, subtext: 'Subtext of item' },
                        { label: 'Library', icon: Search, subtext: 'Subtext of item' }
                    ]
                }
            ],
            [
                {
                    items: [
                        { label: 'Community', icon: Comments, subtext: 'Subtext of item' },
                        { label: 'Rewards', icon: Star, subtext: 'Subtext of item' },
                        { label: 'Investors', icon: Globe, subtext: 'Subtext of item' }
                    ]
                }
            ],
            [
                {
                    items: [{ image: 'https://primefaces.org/cdn/primevue/images/uikit/uikit-system.png', label: 'GET STARTED', subtext: 'Build spectacular apps in no time.' }]
                }
            ]
        ]
    },
    {
        label: 'Resources',
        root: true
    },
    {
        label: 'Contact',
        root: true
    }
]);
<\/script>
```

## Command

The command property of a menuitem defines the callback to run when an item is activated by click or a key event.

```vue
{
    label: 'Log out',
    icon: SignOut,
    command: () => {
        // Callback to run
    }
}
```

## Router

Menu items support navigation via router-link, programmatic routing using commands, or external URLs.

```vue
<template>
    <MegaMenu :model="items">
        <template #item="{ item, icon, label }">
            <router-link v-if="item.route" v-slot="{ href, navigate }" :to="item.route" custom>
                <a v-ripple :href="href" @click="navigate">
                    <component :is="icon" v-if="icon" />
                    <span class="ml-2">{{ label }}</span>
                </a>
            </router-link>
            <a v-else v-ripple :href="item.url" :target="item.target">
                <component :is="icon" v-if="icon" />
                <span class="ml-2">{{ label }}</span>
            </a>
        </template>
    </MegaMenu>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import Home from '@primeicons/vue/home';
import Link from '@primeicons/vue/link';
import Palette from '@primeicons/vue/palette';

const router = useRouter();

const items = ref([
    {
        label: 'Router',
        icon: Palette,
        items: [
            [
                {
                    label: 'Router Link',
                    items: [
                        { label: 'Theming', route: '/theming' },
                        { label: 'UI Kit', route: '/uikit' }
                    ]
                }
            ]
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
            [
                {
                    label: 'External',
                    items: [
                        { label: 'Vue', url: 'https://vuejs.org/', target: '_blank' },
                        { label: 'Vite.js', url: 'https://vitejs.dev/', target: '_blank' }
                    ]
                }
            ]
        ]
    }
]);
<\/script>
```

## Accessibility

Screen Reader MegaMenu component uses the menubar role along with aria-orientation and the value to describe the component can either be provided with aria-labelledby or aria-label props. Each list item has a presentation role whereas anchor elements have a menuitem role with aria-label referring to the label of the item and aria-disabled defined if the item is disabled. A submenu within a MegaMenu uses the menu role with an aria-labelledby defined as the id of the submenu root menuitem label. In addition, root menuitems that open a submenu have aria-haspopup , aria-expanded and aria-controls to define the relation between the item and the submenu. Keyboard Support Key Function tab Add focus to the first item if focus moves in to the menu. If the focus is already within the menu, focus moves to the next focusable item in the page tab sequence. shift + tab Add focus to the last item if focus moves in to the menu. If the focus is already within the menu, focus moves to the previous focusable item in the page tab sequence. enter If menuitem has a submenu, toggles the visibility of the submenu otherwise activates the menuitem and closes all open overlays. space If menuitem has a submenu, toggles the visibility of the submenu otherwise activates the menuitem and closes all open overlays. escape If focus is inside a popup submenu, closes the submenu and moves focus to the root item of the closed submenu. down arrow If focus is on a root element, open a submenu and moves focus to the first element in the submenu otherwise moves focus to the next menuitem within the submenu. up arrow If focus is on a root element, opens a submenu and moves focus to the last element in the submenu otherwise moves focus to the previous menuitem within the submenu. right arrow If focus is on a root element, moves focus to the next menuitem. If the focus in inside a submenu, moves focus to the first menuitem of the next menu group. left arrow If focus is on a root element, moves focus to the previous menuitem. If the focus in inside a submenu, moves focus to the first menuitem of the previous menu group. home Moves focus to the first menuitem within the submenu. end Moves focus to the last menuitem within the submenu.

## Mega Menu API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| model | MenuItem[] | - | An array of menuitems. |
| orientation | any | horizontal | Defines the orientation. |
| breakpoint | string | 960px | The breakpoint to define the maximum width boundary. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| tabindex | string \| number | - | Index of the element in tabbing order. |
| scrollHeight | string | 20rem | Height of the viewport, a scrollbar is defined if height of list exceeds this value. |
| ariaLabel | string | - | Defines a string value that labels an interactive element. |
| ariaLabelledby | string | - | Identifier of the underlying menu element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | MegaMenuPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| rootList | MegaMenuPassThroughOptionType | Used to pass attributes to the root list's DOM element. |
| item | MegaMenuPassThroughOptionType | Used to pass attributes to the  item's DOM element. |
| itemContent | MegaMenuPassThroughOptionType | Used to pass attributes to the item content's DOM element. |
| itemLink | MegaMenuPassThroughOptionType | Used to pass attributes to the item link's DOM element. |
| itemIcon | MegaMenuPassThroughOptionType | Used to pass attributes to the item icon's DOM element. |
| itemLabel | MegaMenuPassThroughOptionType | Used to pass attributes to the item label's DOM element. |
| submenuIcon | MegaMenuPassThroughOptionType | Used to pass attributes to the submenu icon's DOM element. |
| overlay | MegaMenuPassThroughOptionType | Used to pass attributes to the overlay DOM element. |
| grid | MegaMenuPassThroughOptionType | Used to pass attributes to the grid's DOM element. |
| column | MegaMenuPassThroughOptionType | Used to pass attributes to the column's DOM element. |
| submenuLabel | MegaMenuPassThroughOptionType | Used to pass attributes to the submenu item's DOM element. |
| submenu | MegaMenuPassThroughOptionType | Used to pass attributes to the submenu's DOM element. |
| separator | MegaMenuPassThroughOptionType | Used to pass attributes to the separator's DOM element. |
| button | MegaMenuPassThroughOptionType | Used to pass attributes to the mobile popup menu button's DOM element. |
| buttonIcon | MegaMenuPassThroughOptionType | Used to pass attributes to the mobile popup menu button icon's DOM element. |
| start | MegaMenuPassThroughOptionType | Used to pass attributes to the start of the component. |
| end | MegaMenuPassThroughOptionType | Used to pass attributes to the end of the component. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-megamenu | Class name of the root element |
| p-megamenu-start | Class name of the start element |
| p-megamenu-button | Class name of the button element |
| p-megamenu-root-list | Class name of the root list element |
| p-megamenu-submenu-item | Class name of the submenu item element |
| p-megamenu-item | Class name of the item element |
| p-megamenu-item-content | Class name of the item content element |
| p-megamenu-item-link | Class name of the item link element |
| p-megamenu-item-icon | Class name of the item icon element |
| p-megamenu-item-label | Class name of the item label element |
| p-megamenu-submenu-icon | Class name of the submenu icon element |
| p-megamenu-panel | Class name of the panel element |
| p-megamenu-grid | Class name of the grid element |
| p-megamenu-submenu | Class name of the submenu element |
| p-megamenu-submenu-item-label | Class name of the submenu item label element |
| p-megamenu-separator | Class name of the separator element |
| p-megamenu-end | Class name of the end element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| megamenu.background | --p-megamenu-background | Background of root |
| megamenu.border.color | --p-megamenu-border-color | Border color of root |
| megamenu.border.radius | --p-megamenu-border-radius | Border radius of root |
| megamenu.color | --p-megamenu-color | Color of root |
| megamenu.gap | --p-megamenu-gap | Gap of root |
| megamenu.vertical.orientation.padding | --p-megamenu-vertical-orientation-padding | Vertical orientation padding of root |
| megamenu.vertical.orientation.gap | --p-megamenu-vertical-orientation-gap | Vertical orientation gap of root |
| megamenu.horizontal.orientation.padding | --p-megamenu-horizontal-orientation-padding | Horizontal orientation padding of root |
| megamenu.horizontal.orientation.gap | --p-megamenu-horizontal-orientation-gap | Horizontal orientation gap of root |
| megamenu.transition.duration | --p-megamenu-transition-duration | Transition duration of root |
| megamenu.base.item.border.radius | --p-megamenu-base-item-border-radius | Border radius of base item |
| megamenu.base.item.padding | --p-megamenu-base-item-padding | Padding of base item |
| megamenu.item.focus.background | --p-megamenu-item-focus-background | Focus background of item |
| megamenu.item.active.background | --p-megamenu-item-active-background | Active background of item |
| megamenu.item.color | --p-megamenu-item-color | Color of item |
| megamenu.item.focus.color | --p-megamenu-item-focus-color | Focus color of item |
| megamenu.item.active.color | --p-megamenu-item-active-color | Active color of item |
| megamenu.item.padding | --p-megamenu-item-padding | Padding of item |
| megamenu.item.border.radius | --p-megamenu-item-border-radius | Border radius of item |
| megamenu.item.gap | --p-megamenu-item-gap | Gap of item |
| megamenu.item.icon.color | --p-megamenu-item-icon-color | Icon color of item |
| megamenu.item.icon.focus.color | --p-megamenu-item-icon-focus-color | Icon focus color of item |
| megamenu.item.icon.active.color | --p-megamenu-item-icon-active-color | Icon active color of item |
| megamenu.item.icon.size | --p-megamenu-item-icon-size | Icon size of item |
| megamenu.item.label.font.weight | --p-megamenu-item-label-font-weight | Font weight of item label |
| megamenu.item.label.font.size | --p-megamenu-item-label-font-size | Font size of item label |
| megamenu.overlay.padding | --p-megamenu-overlay-padding | Padding of overlay |
| megamenu.overlay.background | --p-megamenu-overlay-background | Background of overlay |
| megamenu.overlay.border.color | --p-megamenu-overlay-border-color | Border color of overlay |
| megamenu.overlay.border.radius | --p-megamenu-overlay-border-radius | Border radius of overlay |
| megamenu.overlay.color | --p-megamenu-overlay-color | Color of overlay |
| megamenu.overlay.shadow | --p-megamenu-overlay-shadow | Shadow of overlay |
| megamenu.overlay.gap | --p-megamenu-overlay-gap | Gap of overlay |
| megamenu.submenu.padding | --p-megamenu-submenu-padding | Padding of submenu |
| megamenu.submenu.gap | --p-megamenu-submenu-gap | Gap of submenu |
| megamenu.submenu.label.padding | --p-megamenu-submenu-label-padding | Padding of submenu label |
| megamenu.submenu.label.font.weight | --p-megamenu-submenu-label-font-weight | Font weight of submenu label |
| megamenu.submenu.label.font.size | --p-megamenu-submenu-label-font-size | Font size of submenu label |
| megamenu.submenu.label.background | --p-megamenu-submenu-label-background | Background of submenu label |
| megamenu.submenu.label.color | --p-megamenu-submenu-label-color | Color of submenu label |
| megamenu.submenu.icon.size | --p-megamenu-submenu-icon-size | Size of submenu icon |
| megamenu.submenu.icon.color | --p-megamenu-submenu-icon-color | Color of submenu icon |
| megamenu.submenu.icon.focus.color | --p-megamenu-submenu-icon-focus-color | Focus color of submenu icon |
| megamenu.submenu.icon.active.color | --p-megamenu-submenu-icon-active-color | Active color of submenu icon |
| megamenu.separator.border.color | --p-megamenu-separator-border-color | Border color of separator |
| megamenu.mobile.button.border.radius | --p-megamenu-mobile-button-border-radius | Border radius of mobile button |
| megamenu.mobile.button.size | --p-megamenu-mobile-button-size | Size of mobile button |
| megamenu.mobile.button.color | --p-megamenu-mobile-button-color | Color of mobile button |
| megamenu.mobile.button.hover.color | --p-megamenu-mobile-button-hover-color | Hover color of mobile button |
| megamenu.mobile.button.hover.background | --p-megamenu-mobile-button-hover-background | Hover background of mobile button |
| megamenu.mobile.button.focus.ring.width | --p-megamenu-mobile-button-focus-ring-width | Focus ring width of mobile button |
| megamenu.mobile.button.focus.ring.style | --p-megamenu-mobile-button-focus-ring-style | Focus ring style of mobile button |
| megamenu.mobile.button.focus.ring.color | --p-megamenu-mobile-button-focus-ring-color | Focus ring color of mobile button |
| megamenu.mobile.button.focus.ring.offset | --p-megamenu-mobile-button-focus-ring-offset | Focus ring offset of mobile button |
| megamenu.mobile.button.focus.ring.shadow | --p-megamenu-mobile-button-focus-ring-shadow | Focus ring shadow of mobile button |

## Menu Item API
