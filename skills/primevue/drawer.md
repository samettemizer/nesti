# Drawer

Drawer is a panel component displayed as an overlay at the edges of the screen.

## Basic

A slide-in panel from the edge of the screen for contextual content.

```vue
<template>
    <div class="flex justify-center">
        <Drawer v-model:visible="visible" header="Basic Drawer" class="w-full! md:w-80!">
            <p>A slide-in panel from the edge of the screen for contextual content.</p>
        </Drawer>
        <Button @click="visible = true" iconOnly>
            <Bars />
        </Button>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Bars from '@primeicons/vue/bars';

const visible = ref(false);
<\/script>
```

## Position

The position of the drawer can be customized with the position property. The available values are left , right , top and bottom .

```vue
<template>
    <div>
        <Drawer v-model:visible="visibleLeft" header="Left Drawer" position="left" class="w-full! md:w-80!">
            <p>The position of the drawer can be customized with the position property. The available values are left, right, top and bottom.</p>
        </Drawer>

        <Drawer v-model:visible="visibleRight" header="Right Drawer" position="right" class="w-full! md:w-80!">
            <p>The position of the drawer can be customized with the position property. The available values are left, right, top and bottom.</p>
        </Drawer>

        <Drawer v-model:visible="visibleTop" header="Top Drawer" position="top" style="height: auto">
            <p>The position of the drawer can be customized with the position property. The available values are left, right, top and bottom.</p>
        </Drawer>

        <Drawer v-model:visible="visibleBottom" header="Bottom Drawer" position="bottom" style="height: auto">
            <p>The position of the drawer can be customized with the position property. The available values are left, right, top and bottom.</p>
        </Drawer>

        <div class="flex gap-2 justify-center">
            <Button @click="visibleLeft = true" iconOnly>
                <ArrowRight />
            </Button>
            <Button @click="visibleRight = true" iconOnly>
                <ArrowLeft />
            </Button>
            <Button @click="visibleTop = true" iconOnly>
                <ArrowDown />
            </Button>
            <Button @click="visibleBottom = true" iconOnly>
                <ArrowUp />
            </Button>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowLeft from '@primeicons/vue/arrow-left';
import ArrowRight from '@primeicons/vue/arrow-right';
import ArrowUp from '@primeicons/vue/arrow-up';

const visibleLeft = ref(false);
const visibleRight = ref(false);
const visibleTop = ref(false);
const visibleBottom = ref(false);
<\/script>
```

## Full Screen

The full screen mode is enabled when position property is set as full .

```vue
<template>
    <div class="flex justify-center">
        <Drawer v-model:visible="visible" header="Full Screen Drawer" position="full">
            <p>The full screen mode is enabled when position property is set as full.</p>
        </Drawer>
        <Button @click="visible = true" iconOnly>
            <WindowMaximize />
        </Button>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import WindowMaximize from '@primeicons/vue/window-maximize';

const visible = ref(false);
<\/script>
```

## Responsive

The responsive mode can be enabled by adding class with responsive utilities.

```vue
<template>
    <div class="flex justify-center">
        <Drawer v-model:visible="visible" header="Responsive Drawer" class="w-full! sm:w-96! md:w-md! lg:w-120!">
            <div class="flex flex-col gap-4">
                <div class="flex flex-col gap-2">
                    <Label for="email" class="font-medium text-sm">Email</Label>
                    <InputText id="email" placeholder="Enter your email" class="w-full" />
                </div>
                <div class="flex flex-col gap-2">
                    <Label for="password" class="font-medium text-sm">Password</Label>
                    <Password input-id="password" placeholder="Enter your password" :feedback="false" class="w-full" :input-style="{ width: '100%' }" />
                </div>
                <div class="flex items-center gap-2">
                    <Checkbox v-model="remember" binary input-id="remember" />
                    <Label for="remember" class="text-sm">Remember me</Label>
                </div>
                <Button class="w-full">Sign In</Button>
            </div>
        </Drawer>
        <Button @click="visible = true">Log in</Button>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
const remember = ref(false);
<\/script>
```

## Template

Drawer is customizable by header , content , footer templates.

```vue
<template>
    <div class="flex justify-center">
        <Drawer v-model:visible="visible" :closable="false">
            <template #header>
                <div class="flex items-center gap-2">
                    <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
                    <span class="font-bold">Amy Elsner</span>
                </div>
            </template>
            <p class="text-sm">
                Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
                consequat.
            </p>
            <template #footer>
                <div class="flex items-center gap-2">
                    <Button class="w-full" variant="outlined">
                        <User />
                        Account
                    </Button>
                    <Button class="w-full" severity="danger" text>
                        <SignOut />
                        Logout
                    </Button>
                </div>
            </template>
        </Drawer>
        <Button @click="visible = true" iconOnly>
            <Plus />
        </Button>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Plus from '@primeicons/vue/plus';
import SignOut from '@primeicons/vue/sign-out';
import User from '@primeicons/vue/user';

const visible = ref(false);
<\/script>
```

## Headless

Headless mode allows you to customize the entire user interface instead of the default elements.

```vue
<template>
    <div class="flex justify-center">
        <Drawer v-model:visible="visible">
            <template #container="{ closeCallback }">
                <div class="flex flex-col h-full">
                    <div class="flex items-center justify-between px-5 pt-3 shrink-0">
                        <span class="inline-flex items-center gap-2">
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
                            <span class="font-semibold text-xl text-primary">Your Logo</span>
                        </span>
                        <span>
                            <Button type="button" @click="closeCallback" rounded variant="outlined" iconOnly class="h-8 w-8">
                                <Times />
                            </Button>
                        </span>
                    </div>
                    <div class="overflow-y-auto">
                        <ul class="list-none p-3 m-0">
                            <li>
                                <div
                                    v-ripple
                                    v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-slidedown', leaveToClass: 'hidden', leaveActiveClass: 'animate-slideup' }"
                                    class="p-3 flex items-center justify-between text-surface-600 dark:text-surface-200 cursor-pointer p-ripple"
                                >
                                    <span class="font-medium text-sm">FAVORITES</span>
                                    <ChevronDown />
                                </div>
                                <ul class="list-none p-0 m-0 overflow-hidden">
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><Home /></span>
                                            <span class="font-medium text-sm">Dashboard</span>
                                        </a>
                                    </li>
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><Bookmark /></span>
                                            <span class="font-medium text-sm">Bookmarks</span>
                                        </a>
                                    </li>
                                    <li>
                                        <a
                                            v-ripple
                                            v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-slidedown', leaveToClass: 'hidden', leaveActiveClass: 'animate-slideup' }"
                                            class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple"
                                        >
                                            <span class="mr-2"><ChartLine /></span>
                                            <span class="font-medium text-sm">Reports</span>
                                            <span class="ml-auto"><ChevronDown /></span>
                                        </a>
                                        <ul class="list-none py-0 pl-4 pr-0 m-0 hidden overflow-y-hidden transition-all duration-[400ms] ease-in-out">
                                            <li>
                                                <a
                                                    v-ripple
                                                    v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-slidedown', leaveToClass: 'hidden', leaveActiveClass: 'animate-slideup' }"
                                                    class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple"
                                                >
                                                    <span class="mr-2"><ChartLine /></span>
                                                    <span class="font-medium text-sm">Revenue</span>
                                                    <span class="ml-auto"><ChevronDown /></span>
                                                </a>
                                                <ul class="list-none py-0 pl-4 pr-0 m-0 hidden overflow-y-hidden transition-all duration-[400ms] ease-in-out">
                                                    <li>
                                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                                            <span class="mr-2"><Table /></span>
                                                            <span class="font-medium text-sm">View</span>
                                                        </a>
                                                    </li>
                                                    <li>
                                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                                            <span class="mr-2"><Search /></span>
                                                            <span class="font-medium text-sm">Search</span>
                                                        </a>
                                                    </li>
                                                </ul>
                                            </li>
                                            <li>
                                                <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                                    <span class="mr-2"><ChartLine /></span>
                                                    <span class="font-medium text-sm">Expenses</span>
                                                </a>
                                            </li>
                                        </ul>
                                    </li>
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><Users /></span>
                                            <span class="font-medium text-sm">Team</span>
                                        </a>
                                    </li>
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><Comments /></span>
                                            <span class="font-medium text-sm">Messages</span>
                                            <span class="inline-flex items-center justify-center ml-auto bg-primary text-primary-contrast rounded-full text-sm" style="min-width: 1.4rem; height: 1.4rem">3</span>
                                        </a>
                                    </li>
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><CalendarIcon /></span>
                                            <span class="font-medium text-sm">Calendar</span>
                                        </a>
                                    </li>
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><Cog /></span>
                                            <span class="font-medium text-sm">Settings</span>
                                        </a>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                        <ul class="list-none p-3 m-0">
                            <li>
                                <div
                                    v-ripple
                                    v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-slidedown', leaveToClass: 'hidden', leaveActiveClass: 'animate-slideup' }"
                                    class="p-3 flex items-center justify-between text-surface-600 dark:text-surface-200 cursor-pointer p-ripple"
                                >
                                    <span class="font-medium text-sm">APPLICATION</span>
                                    <ChevronDown />
                                </div>
                                <ul class="list-none p-0 m-0 overflow-hidden">
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><Folder /></span>
                                            <span class="font-medium text-sm">Projects</span>
                                        </a>
                                    </li>
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><ChartBar /></span>
                                            <span class="font-medium text-sm">Performance</span>
                                        </a>
                                    </li>
                                    <li>
                                        <a v-ripple class="flex items-center cursor-pointer p-3 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                                            <span class="mr-2"><Cog /></span>
                                            <span class="font-medium text-sm">Settings</span>
                                        </a>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                    <div class="mt-auto">
                        <hr class="mb-3 mx-3 border-t border-0 border-surface" />
                        <a v-ripple class="m-3 flex items-center cursor-pointer p-3 gap-2 rounded-border text-surface-700 dark:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-700 duration-150 transition-colors p-ripple">
                            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
                            <span class="font-bold text-sm">Amy Elsner</span>
                        </a>
                    </div>
                </div>
            </template>
        </Drawer>
        <Button @click="visible = true" iconOnly>
            <Bars />
        </Button>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Bars from '@primeicons/vue/bars';
import Bookmark from '@primeicons/vue/bookmark';
import CalendarIcon from '@primeicons/vue/calendar';
import ChartBar from '@primeicons/vue/chart-bar';
import ChartLine from '@primeicons/vue/chart-line';
import ChevronDown from '@primeicons/vue/chevron-down';
import Cog from '@primeicons/vue/cog';
import Comments from '@primeicons/vue/comments';
import Folder from '@primeicons/vue/folder';
import Home from '@primeicons/vue/home';
import Search from '@primeicons/vue/search';
import Table from '@primeicons/vue/table';
import Times from '@primeicons/vue/times';
import Users from '@primeicons/vue/users';

const visible = ref(false);
<\/script>
```

## Accessibility

Screen Reader Drawer component uses complementary role by default, since any attribute is passed to the root element aria role can be changed depending on your use case and additional attributes like aria-labelledby can be added. In addition aria-modal is added since focus is kept within the drawer when opened. It is recommended to use a trigger component that can be accessed with keyboard such as a button, if not adding tabIndex would be necessary. Trigger element also requires aria-expanded and aria-controls to be handled explicitly. Overlay Keyboard Support Key Function tab Moves focus to the next the focusable element within the drawer. shift + tab Moves focus to the previous the focusable element within the drawer. escape Closes the dialog if closeOnEscape is true. Close Button Keyboard Support Key Function enter Closes the drawer. space Closes the drawer.

```vue
<template>
    <Button @click="visible = true" :aria-controls="visible ? 'sbar' : null" :aria-expanded="visible">
        <ExternalLink />
        Show
    </Button>

    <Drawer id="sbar" v-model:visible="visible" role="region" >
        <p>Content</p>
    </Drawer>
</template>

<script setup>
import ExternalLink from '@primeicons/vue/external-link';
<\/script>
```

## Drawer API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| visible | boolean | false | Specifies the visibility of the dialog. |
| position | any | left | Specifies the position of the drawer. |
| header | string | - | Title content of the dialog. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| dismissable | boolean | true | Whether clicking outside closes the panel. |
| showCloseIcon | boolean | true | Whether to display a close icon inside the panel. |
| closeButtonProps | object | - | Used to pass the custom value to read for the button inside the component. |
| closeIcon | string | - | Icon to display in the drawer close button. |
| modal | boolean | true | Whether to a modal layer behind the drawer. |
| blockScroll | boolean | false | Whether background scroll should be blocked when drawer is visible. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |
| closeOnEscape | boolean | true | Specifies if pressing escape key should hide the drawer. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | DrawerPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| header | DrawerPassThroughOptionType | Used to pass attributes to the header's DOM element. |
| title | DrawerPassThroughOptionType | Used to pass attributes to the header content's DOM element. |
| pcCloseButton | any | Used to pass attributes to the close button's DOM element. |
| content | DrawerPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| footer | DrawerPassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| mask | DrawerPassThroughOptionType | Used to pass attributes to the mask's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | DrawerPassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-drawer-mask | Class name of the mask element |
| p-drawer | Class name of the root element |
| p-drawer-header | Class name of the header element |
| p-drawer-title | Class name of the title element |
| p-drawer-close-button | Class name of the close button element |
| p-drawer-content | Class name of the content element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| drawer.background | --p-drawer-background | Background of root |
| drawer.border.color | --p-drawer-border-color | Border color of root |
| drawer.color | --p-drawer-color | Color of root |
| drawer.shadow | --p-drawer-shadow | Shadow of root |
| drawer.header.padding | --p-drawer-header-padding | Padding of header |
| drawer.title.font.size | --p-drawer-title-font-size | Font size of title |
| drawer.title.font.weight | --p-drawer-title-font-weight | Font weight of title |
| drawer.content.padding | --p-drawer-content-padding | Padding of content |
| drawer.footer.padding | --p-drawer-footer-padding | Padding of footer |
