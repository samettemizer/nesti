# Tabs

Tabs is a container component to group content with tabs.

## Basic

Organizes content into selectable, horizontally laid out sections.

```vue
<template>
    <Tabs value="tab1">
        <TabList>
            <Tab value="tab1">Account Info</Tab>
            <Tab value="tab2">Payment</Tab>
            <Tab value="tab3">Preferences</Tab>
        </TabList>
        <TabPanels>
            <TabPanel value="tab1">
                <h2 class="text-lg font-bold">Account Info</h2>
                <p class="text-surface-500 mt-1">Update your personal information such as name, email address, and profile picture.</p>
            </TabPanel>
            <TabPanel value="tab2">
                <h2 class="text-lg font-bold">Payment</h2>
                <p class="text-surface-500 mt-1">Manage your subscription plan, view invoices, and update your payment method.</p>
            </TabPanel>
            <TabPanel value="tab3">
                <h2 class="text-lg font-bold">Preferences</h2>
                <p class="text-surface-500 mt-1">Customize how the application looks and behaves to match your personal preferences.</p>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>
```

## Dynamic

Create tabs from an array to keep labels and panel content in sync.

```vue
<template>
    <Tabs value="tab1">
        <TabList>
            <Tab v-for="tab in tabs" :key="tab.id" :value="tab.id">{{ tab.title }}</Tab>
        </TabList>
        <TabPanels>
            <TabPanel v-for="tab in tabs" :key="tab.id" :value="tab.id">
                <h2 class="text-lg font-bold">{{ tab.title }}</h2>
                <p class="text-surface-500 mt-1">{{ tab.content }}</p>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>

<script setup>
import { ref } from 'vue';

const tabs = ref([
    { id: 'tab1', title: 'Account Info', content: 'Update your personal information such as name, email address, and profile picture.' },
    { id: 'tab2', title: 'Payment', content: 'Manage your subscription plan, view invoices, and update your payment method.' },
    { id: 'tab3', title: 'Preferences', content: 'Customize how the application looks and behaves to match your personal preferences.' }
]);
<\/script>
```

## Controlled

Control the active tab with the value property.

```vue
<template>
    <div class="space-y-4">
        <Button type="button" @click="value = 'tab2'">Go to Payment</Button>
        <Tabs v-model:value="value">
            <TabList>
                <Tab v-for="tab in tabs" :key="tab.id" :value="tab.id">{{ tab.title }}</Tab>
            </TabList>
            <TabPanels>
                <TabPanel v-for="tab in tabs" :key="tab.id" :value="tab.id">
                    <h2 class="text-lg font-bold">{{ tab.title }}</h2>
                    <p class="text-surface-500 mt-1">{{ tab.content }}</p>
                </TabPanel>
            </TabPanels>
        </Tabs>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('tab1');
const tabs = ref([
    { id: 'tab1', title: 'Account Info', content: 'Update your personal information such as name, email address, and profile picture.' },
    { id: 'tab2', title: 'Payment', content: 'Manage your subscription plan, view invoices, and update your payment method.' },
    { id: 'tab3', title: 'Preferences', content: 'Customize how the application looks and behaves to match your personal preferences.' }
]);
<\/script>
```

## Scrollable

Long tab lists are navigable by default; previous and next buttons appear automatically when the tabs overflow the available width.

```vue
<template>
    <Tabs value="0" scrollable>
        <TabList>
            <Tab v-for="tab in scrollableTabs" :key="tab.value" :value="tab.value">{{ tab.title }}</Tab>
        </TabList>
        <TabPanels>
            <TabPanel v-for="tab in scrollableTabs" :key="tab.value" :value="tab.value">
                <h2 class="text-lg font-bold">{{ tab.title }}</h2>
                <p class="text-surface-500 mt-1">{{ tab.content }}</p>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>

<script setup>
import { ref } from 'vue';

const sentences = [
    'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
    'Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
    'Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.',
    'Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore.',
    'Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia.',
    'Curabitur pretium tincidunt lacus, nec viverra velit semper at.',
    'Fusce condimentum nunc ac nisi vulputate fringilla.',
    'Donec fermentum porttitor nunc, vitae pellentesque tortor.',
    'Pellentesque habitant morbi tristique senectus et netus et malesuada fames.',
    'Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia.'
];

const scrollableTabs = ref(
    Array.from({ length: 50 }, (_, i) => {
        const start = i % sentences.length;
        const content = Array.from({ length: 4 }, (_, j) => sentences[(start + j) % sentences.length]).join(' ');

        return { title: \`Tab \${i + 1}\`, value: \`\${i}\`, content };
    })
);
<\/script>
```

## Select on Focus

Set selectOnFocus to activate tabs on focus.

```vue
<template>
    <Tabs value="tab1" selectOnFocus>
        <TabList>
            <Tab v-for="tab in tabs" :key="tab.id" :value="tab.id">{{ tab.title }}</Tab>
        </TabList>
        <TabPanels>
            <TabPanel v-for="tab in tabs" :key="tab.id" :value="tab.id">
                <h2 class="text-lg font-bold">{{ tab.title }}</h2>
                <p class="text-surface-500 mt-1">{{ tab.content }}</p>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>

<script setup>
import { ref } from 'vue';

const tabs = ref([
    { id: 'tab1', title: 'Account Info', content: 'Update your personal information such as name, email address, and profile picture.' },
    { id: 'tab2', title: 'Payment', content: 'Manage your subscription plan, view invoices, and update your payment method.' },
    { id: 'tab3', title: 'Preferences', content: 'Customize how the application looks and behaves to match your personal preferences.' }
]);
<\/script>
```

## Lazy

By default, inactive tab's content is rendered (but hidden). You can use the lazy property (either globally on Tabs or individually on a TabPanel ) to change this behavior so that content is only rendered when the tab becomes active. This is useful when a tab contains complex components that should only be initialized once the tab is activated.

```vue
<template>
    <Tabs lazy value="0">
        <TabList>
            <Tab value="0">Header I</Tab>
            <Tab value="1">Header II</Tab>
            <Tab value="2">Header III</Tab>
        </TabList>
        <TabPanels>
            <TabPanel value="0">
                <p class="m-0 text-sm">
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
                    consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
                </p>
            </TabPanel>
            <TabPanel value="1">
                <p class="m-0 text-sm">
                    Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim
                    ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Consectetur, adipisci velit, sed quia non numquam eius modi.
                </p>
            </TabPanel>
            <TabPanel value="2">
                <p class="m-0 text-sm">Complex components that should only be initialized when the tab becomes active</p>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>
```

## Disabled

Set disabled on a Tab to prevent selection.

```vue
<template>
    <Tabs value="tab1">
        <TabList>
            <Tab value="tab1">Account Info</Tab>
            <Tab value="tab2" disabled>Payment</Tab>
            <Tab value="tab3">Preferences</Tab>
        </TabList>
        <TabPanels>
            <TabPanel value="tab1">
                <h2 class="text-lg font-bold">Account Info</h2>
                <p class="text-surface-500 mt-1">Update your personal information such as name, email address, and profile picture.</p>
            </TabPanel>
            <TabPanel value="tab2">
                <h2 class="text-lg font-bold">Payment</h2>
                <p class="text-surface-500 mt-1">Manage your subscription plan, view invoices, and update your payment method.</p>
            </TabPanel>
            <TabPanel value="tab3">
                <h2 class="text-lg font-bold">Preferences</h2>
                <p class="text-surface-500 mt-1">Customize how the application looks and behaves to match your personal preferences.</p>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>
```

## Custom Indicator

The active tab highlight can be restyled into a custom indicator through the activeBar pass through option, using the --px-active-bar-* CSS variables that hold the active tab's position and size.

```vue
<template>
    <Tabs value="tab1">
        <TabList
            :pt="{
                activeBar: {
                    class: 'w-[calc(var(--px-active-bar-width)-10px)]! h-[calc(var(--px-active-bar-height)-16px)]! left-[calc(var(--px-active-bar-left)+5px)]! top-[calc(var(--px-active-bar-top)+8px)]! bg-surface-100! dark:bg-surface-800! rounded-md! transition-[left,width]! duration-200!'
                }
            }"
        >
            <Tab v-for="tab in tabs" :key="tab.id" :value="tab.id" class="z-10">{{ tab.title }}</Tab>
        </TabList>
        <TabPanels>
            <TabPanel v-for="tab in tabs" :key="tab.id" :value="tab.id">
                <h2 class="text-lg font-bold">{{ tab.title }}</h2>
                <p class="text-surface-500 mt-1">{{ tab.content }}</p>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>

<script setup>
import { ref } from 'vue';

const tabs = ref([
    { id: 'tab1', title: 'Account Info', content: 'Update your personal information such as name, email address, and profile picture.' },
    { id: 'tab2', title: 'Payment', content: 'Manage your subscription plan, view invoices, and update your payment method.' },
    { id: 'tab3', title: 'Preferences', content: 'Customize how the application looks and behaves to match your personal preferences.' }
]);
<\/script>
```

## Template

Use custom markup inside tabs and panels to build richer tab content.

```vue
<template>
    <Tabs value="tab1" class="max-w-md mx-auto">
        <TabList>
            <Tab value="tab1" class="flex items-center gap-2!">
                <User />
                Account Info
            </Tab>
            <Tab value="tab2" class="flex items-center gap-2!">
                <CreditCard />
                Payment
                <Badge size="small" value="New" />
            </Tab>
            <Tab value="tab3" class="flex items-center gap-2!">
                <Cog />
                Preferences
            </Tab>
        </TabList>
        <TabPanels>
            <TabPanel value="tab1">
                <div>
                    <p class="mt-2 mb-8 text-surface-500">Update your personal information such as name, email address, and profile picture.</p>
                    <div class="space-y-4">
                        <div class="flex flex-col gap-1">
                            <Label for="username">Username</Label>
                            <InputText id="username" placeholder="john.doe" />
                        </div>
                        <div class="flex flex-col gap-1">
                            <Label for="email">Email</Label>
                            <InputText id="email" placeholder="john.doe@example.com" />
                        </div>
                    </div>
                    <Button class="mt-8 w-fit">Save Changes</Button>
                </div>
            </TabPanel>
            <TabPanel value="tab2">
                <div>
                    <p class="mt-2 mb-8 text-surface-500">Manage your subscription plan, view invoices, and update your payment method.</p>
                    <div class="space-y-4">
                        <div class="flex flex-col gap-1">
                            <Label for="cardName">Cardholder Name</Label>
                            <InputText id="cardName" placeholder="John Doe" />
                        </div>
                        <div class="flex flex-col gap-1">
                            <Label for="cardNumber">Card Number</Label>
                            <InputText id="cardNumber" placeholder="0000 0000 0000 0000" />
                        </div>
                        <div class="flex flex-col gap-1">
                            <Label for="expiryDate">Expiry Date</Label>
                            <InputText id="expiryDate" placeholder="MM/YY" />
                        </div>
                    </div>
                    <Button class="mt-8 w-fit">Update Payment</Button>
                </div>
            </TabPanel>
            <TabPanel value="tab3">
                <div>
                    <p class="mt-2 mb-8 text-surface-500">Customize how the application looks and behaves to match your personal preferences.</p>
                    <div class="space-y-4">
                        <div class="flex items-center justify-between">
                            <Label for="darkMode">Dark Mode</Label>
                            <ToggleSwitch v-model="darkMode" inputId="darkMode" />
                        </div>
                        <div class="flex items-center justify-between">
                            <Label for="emailNotifications">Email Notifications</Label>
                            <ToggleSwitch v-model="emailNotifications" inputId="emailNotifications" />
                        </div>
                        <div class="flex items-center justify-between">
                            <Label for="desktopNotifications">Desktop Notifications</Label>
                            <ToggleSwitch v-model="desktopNotifications" inputId="desktopNotifications" />
                        </div>
                    </div>
                    <Button class="w-fit mt-8 ml-auto mr-0">Save Preferences</Button>
                </div>
            </TabPanel>
        </TabPanels>
    </Tabs>
</template>

<script setup>
import { ref } from 'vue';
import Cog from '@primeicons/vue/cog';
import CreditCard from '@primeicons/vue/credit-card';
import User from '@primeicons/vue/user';

const darkMode = ref(false);
const emailNotifications = ref(true);
const desktopNotifications = ref(false);
<\/script>
```

## Tab Menu

A navigation menu is implemented using tabs without the panels where the content of a tab is provided by a route component like router-view . For the purpose of this demo, router-view is not included.

```vue
<template>
    <Tabs value="dashboard">
        <TabList>
            <Tab v-for="tab in tabs" :key="tab.route" :value="tab.route" as="div" class="flex items-center gap-2! text-inherit">
                <router-link v-slot="{ href, navigate }" :to="tab.route" custom>
                    <a :href="href" @click="navigate" class="flex items-center gap-2 text-inherit">
                        <component :is="tab.icon" />
                        <span>{{ tab.label }}</span>
                    </a>
                </router-link>
            </Tab>
        </TabList>
    </Tabs>
    <!-- <router-view /> -->
</template>

<script setup>
import ChartLine from '@primeicons/vue/chart-line';
import Home from '@primeicons/vue/home';
import Inbox from '@primeicons/vue/inbox';
import List from '@primeicons/vue/list';

const tabs = [
    { route: 'dashboard', label: 'Dashboard', icon: Home },
    { route: 'transactions', label: 'Transactions', icon: ChartLine },
    { route: 'products', label: 'Products', icon: List },
    { route: 'messages', label: 'Messages', icon: Inbox }
];
<\/script>
```

## Accessibility

Screen Reader The tabs container in TabList is defined with the tablist role, as any attribute is passed to the container element aria-labelledby can be optionally used to specify an element to describe the Tabs. Each Tab has a tab role along with aria-selected state attribute and aria-controls to refer to the corresponding TabPanel. TabPanel has tabpanel role, an id to match the aria-controls of Tab and aria-labelledby reference to Tab as the accessible name. Tab Keyboard Support Key Function tab Moves focus through the header. enter Activates the focused tab header. space Activates the focused tab header. right arrow Moves focus to the next header. If focus is on the last header, moves focus to the first header. left arrow Moves focus to the previous header. If focus is on the first header, moves focus to the last header. home Moves focus to the last header. end Moves focus to the first header. pageUp Moves scroll position to first header. pageDown Moves scroll position to last header.

## Tabs API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | - | Value of the active tab. |
| lazy | boolean | false | When enabled, hidden tabs are not rendered at all. Defaults to false that hides tabs with css. |
| showNavigators | boolean | true | Whether to display navigation buttons when the tablist overflows. |
| tabindex | number | 0 | Index of the element in tabbing order. |
| selectOnFocus | boolean | false | When enabled, the focused tab is activated. |
| scrollable | boolean | false | When specified, enables horizontal and/or vertical scrolling. |
| scrollStrategy | "center" \| "nearest" \| Function | 'nearest' | Defines how the active tab is scrolled into view when it changes. -  `'nearest'` : scrolls only if the tab is clipped or too close to an edge, with padding. -  `'center'` : always centers the active tab in the viewport. -  `function` : a custom scroll function receiving the content element and active tab element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TabsPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-tabs | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| tabs.transition.duration | --p-tabs-transition-duration | Transition duration of root |
| tabs.tablist.border.width | --p-tabs-tablist-border-width | Border width of tablist |
| tabs.tablist.background | --p-tabs-tablist-background | Background of tablist |
| tabs.tablist.border.color | --p-tabs-tablist-border-color | Border color of tablist |
| tabs.tab.background | --p-tabs-tab-background | Background of tab |
| tabs.tab.hover.background | --p-tabs-tab-hover-background | Hover background of tab |
| tabs.tab.active.background | --p-tabs-tab-active-background | Active background of tab |
| tabs.tab.border.width | --p-tabs-tab-border-width | Border width of tab |
| tabs.tab.border.color | --p-tabs-tab-border-color | Border color of tab |
| tabs.tab.hover.border.color | --p-tabs-tab-hover-border-color | Hover border color of tab |
| tabs.tab.active.border.color | --p-tabs-tab-active-border-color | Active border color of tab |
| tabs.tab.color | --p-tabs-tab-color | Color of tab |
| tabs.tab.hover.color | --p-tabs-tab-hover-color | Hover color of tab |
| tabs.tab.active.color | --p-tabs-tab-active-color | Active color of tab |
| tabs.tab.padding | --p-tabs-tab-padding | Padding of tab |
| tabs.tab.font.weight | --p-tabs-tab-font-weight | Font weight of tab |
| tabs.tab.font.size | --p-tabs-tab-font-size | Font size of tab |
| tabs.tab.margin | --p-tabs-tab-margin | Margin of tab |
| tabs.tab.gap | --p-tabs-tab-gap | Gap of tab |
| tabs.tab.focus.ring.width | --p-tabs-tab-focus-ring-width | Focus ring width of tab |
| tabs.tab.focus.ring.style | --p-tabs-tab-focus-ring-style | Focus ring style of tab |
| tabs.tab.focus.ring.color | --p-tabs-tab-focus-ring-color | Focus ring color of tab |
| tabs.tab.focus.ring.offset | --p-tabs-tab-focus-ring-offset | Focus ring offset of tab |
| tabs.tab.focus.ring.shadow | --p-tabs-tab-focus-ring-shadow | Focus ring shadow of tab |
| tabs.tabpanel.background | --p-tabs-tabpanel-background | Background of tabpanel |
| tabs.tabpanel.color | --p-tabs-tabpanel-color | Color of tabpanel |
| tabs.tabpanel.padding | --p-tabs-tabpanel-padding | Padding of tabpanel |
| tabs.tabpanel.focus.ring.width | --p-tabs-tabpanel-focus-ring-width | Focus ring width of tabpanel |
| tabs.tabpanel.focus.ring.style | --p-tabs-tabpanel-focus-ring-style | Focus ring style of tabpanel |
| tabs.tabpanel.focus.ring.color | --p-tabs-tabpanel-focus-ring-color | Focus ring color of tabpanel |
| tabs.tabpanel.focus.ring.offset | --p-tabs-tabpanel-focus-ring-offset | Focus ring offset of tabpanel |
| tabs.tabpanel.focus.ring.shadow | --p-tabs-tabpanel-focus-ring-shadow | Focus ring shadow of tabpanel |
| tabs.nav.button.background | --p-tabs-nav-button-background | Background of nav button |
| tabs.nav.button.color | --p-tabs-nav-button-color | Color of nav button |
| tabs.nav.button.hover.color | --p-tabs-nav-button-hover-color | Hover color of nav button |
| tabs.nav.button.width | --p-tabs-nav-button-width | Width of nav button |
| tabs.nav.button.focus.ring.width | --p-tabs-nav-button-focus-ring-width | Focus ring width of nav button |
| tabs.nav.button.focus.ring.style | --p-tabs-nav-button-focus-ring-style | Focus ring style of nav button |
| tabs.nav.button.focus.ring.color | --p-tabs-nav-button-focus-ring-color | Focus ring color of nav button |
| tabs.nav.button.focus.ring.offset | --p-tabs-nav-button-focus-ring-offset | Focus ring offset of nav button |
| tabs.nav.button.focus.ring.shadow | --p-tabs-nav-button-focus-ring-shadow | Focus ring shadow of nav button |
| tabs.nav.button.shadow | --p-tabs-nav-button-shadow | Shadow of nav button |
| tabs.active.bar.height | --p-tabs-active-bar-height | Height of active bar |
| tabs.active.bar.bottom | --p-tabs-active-bar-bottom | Bottom of active bar |
| tabs.active.bar.background | --p-tabs-active-bar-background | Background of active bar |

## Tab List API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TabListPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| prevButton | TabListPassThroughOptionType | Used to pass attributes to the previous button component. |
| nextButton | TabListPassThroughOptionType | Used to pass attributes to the next button component. |
| content | TabListPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| activeBar | TabListPassThroughOptionType | Used to pass attributes to the inkbar's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-tablist | Class name of the root element |
| p-tablist-content | Class name of the content element |
| p-tablist-active-bar | Class name of the activebar element |
| p-tablist-prev-button | Class name of the previous button element |
| p-tablist-next-button | Class name of the next button element |

## Tab API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | - | Value of tab. |
| disabled | boolean | false | Whether the tab is disabled. |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TabPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-tab | Class name of the root element |

## Tab Panels API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TabPanelsPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-tabpanels | Class name of the root element |

## Tab Panel API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | - | Value of tabpanel. |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TabPanelPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-tabpanel | Class name of the root element |
