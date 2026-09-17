# Accordion

Accordion groups a collection of contents in tabs.

## Basic

A simple accordion with expandable panels controlled via the value prop.

```vue
<template>
    <div class="flex justify-center">
        <Accordion class="w-full max-w-md">
            <AccordionPanel value="0">
                <AccordionHeader>What is this service about?</AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">This service helps you manage your projects more efficiently by offering real-time collaboration, task tracking, and powerful analytics.</p>
                </AccordionContent>
            </AccordionPanel>
            <AccordionPanel value="1">
                <AccordionHeader>Is my data secure?</AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">Yes. We use end-to-end encryption and follow industry best practices to ensure your data is protected. Your information is stored on secure servers and regularly backed up.</p>
                </AccordionContent>
            </AccordionPanel>
            <AccordionPanel value="2">
                <AccordionHeader>Can I upgrade or downgrade my plan later?</AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">Absolutely. You can change your subscription plan at any time from your account settings. Changes take effect immediately, and any billing adjustments are handled automatically.</p>
                </AccordionContent>
            </AccordionPanel>
        </Accordion>
    </div>
</template>
```

## Multiple

By default, a single panel is open at a time. Enable multiple to allow multiple panels to stay open.

```vue
<template>
    <div class="flex justify-center">
        <Accordion v-model:value="active" multiple class="w-full max-w-md">
            <AccordionPanel value="0">
                <AccordionHeader>What is this service about?</AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">
                        This service helps you manage your projects more efficiently by offering real-time collaboration, task tracking, and powerful analytics. Whether you're working solo or in a team, it's built to scale with your needs.
                    </p>
                </AccordionContent>
            </AccordionPanel>
            <AccordionPanel value="1">
                <AccordionHeader>Is my data secure?</AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">Yes. We use end-to-end encryption and follow industry best practices to ensure your data is protected. Your information is stored on secure servers and regularly backed up.</p>
                </AccordionContent>
            </AccordionPanel>
            <AccordionPanel value="2">
                <AccordionHeader>Can I upgrade or downgrade my plan later?</AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">Absolutely. You can change your subscription plan at any time from your account settings. Changes take effect immediately, and any billing adjustments are handled automatically.</p>
                </AccordionContent>
            </AccordionPanel>
        </Accordion>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const active = ref(null);
<\/script>
```

## Controlled

Control the active panel state with value and update:value .

```vue
<template>
    <div class="flex justify-center">
        <div class="w-full max-w-md space-y-4">
            <div class="flex gap-2 justify-center">
                <Button type="button" :severity="active === '0' ? 'primary' : 'secondary'" @click="active = '0'">Panel 1</Button>
                <Button type="button" :severity="active === '1' ? 'primary' : 'secondary'" @click="active = '1'">Panel 2</Button>
                <Button type="button" :severity="active === '2' ? 'primary' : 'secondary'" @click="active = '2'">Panel 3</Button>
                <Button type="button" severity="danger" @click="active = null">Close All</Button>
            </div>
            <Accordion v-model:value="active">
                <AccordionPanel value="0">
                    <AccordionHeader>What is this service about?</AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">This service helps you manage your projects more efficiently by offering real-time collaboration, task tracking, and powerful analytics.</p>
                    </AccordionContent>
                </AccordionPanel>
                <AccordionPanel value="1">
                    <AccordionHeader>Is my data secure?</AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">Yes. We use end-to-end encryption and follow industry best practices to ensure your data is protected. Your information is stored on secure servers and regularly backed up.</p>
                    </AccordionContent>
                </AccordionPanel>
                <AccordionPanel value="2">
                    <AccordionHeader>Can I upgrade or downgrade my plan later?</AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">Absolutely. You can change your subscription plan at any time from your account settings. Changes take effect immediately, and any billing adjustments are handled automatically.</p>
                    </AccordionContent>
                </AccordionPanel>
            </Accordion>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const active = ref('0');
<\/script>
```

## Trigger

The trigger can be tailored per panel; the toggleicon slot animates a custom icon via the header's data-p attribute, while the asChild slot exposes onClick and active so the toggle can be rendered as any element, such as a Button .

```vue
<template>
    <Accordion class="max-w-md mx-auto" multiple>
        <AccordionPanel value="1">
            <AccordionHeader>
                <template #toggleicon>
                    <Plus class="transition-transform ease-out in-data-[p=active]:rotate-45" />
                </template>
                What is this service about?
            </AccordionHeader>
            <AccordionContent>
                <p class="m-0 text-sm">
                    This service helps you manage your projects more efficiently by offering real-time collaboration, task tracking, and powerful analytics. Whether you're working solo or in a team, it's built to scale with your needs.
                </p>
            </AccordionContent>
        </AccordionPanel>
        <AccordionPanel value="2">
            <AccordionHeader asChild>
                <template #default="{ active, a11yAttrs, onClick }">
                    <div class="flex items-center justify-between gap-4 p-4 bg-(--p-accordion-header-background)">
                        <span class="text-sm font-semibold text-(--p-accordion-header-color)">Is my data secure?</span>
                        <Button variant="outlined" size="small" v-bind="a11yAttrs" @click="onClick">{{ active ? 'Hide' : 'Show' }}</Button>
                    </div>
                </template>
            </AccordionHeader>
            <AccordionContent>
                <p class="m-0 text-sm">Yes. We use end-to-end encryption and follow industry best practices to ensure your data is protected. Your information is stored on secure servers and regularly backed up.</p>
            </AccordionContent>
        </AccordionPanel>
        <AccordionPanel value="3">
            <AccordionHeader>
                <template #toggleicon><span class="hidden" /></template>
                <span class="inline-flex items-center gap-2">
                    <Plus class="transition-transform ease-out in-data-[p=active]:rotate-45" />
                    Can I upgrade or downgrade my plan later?
                </span>
            </AccordionHeader>
            <AccordionContent>
                <p class="m-0 text-sm">Absolutely. You can change your subscription plan at any time from your account settings. Changes take effect immediately, and any billing adjustments are handled automatically.</p>
            </AccordionContent>
        </AccordionPanel>
    </Accordion>
</template>

<script setup>
import Plus from '@primeicons/vue/plus';
<\/script>
```

## Indicator

The toggleicon slot customizes the indicator. It can switch between two icons using the active context variable, or render a single icon that animates purely with CSS by targeting the header's data-p attribute.

```vue
<template>
    <div class="flex flex-col gap-8">
        <div>
            <h3 class="text-sm! font-medium! text-surface-500! mb-2">Match open / closed</h3>
            <Accordion class="max-w-md mx-auto">
                <AccordionPanel value="1">
                    <AccordionHeader>
                        <template #toggleicon="{ active }">
                            <Minus v-if="active" />
                            <Plus v-else />
                        </template>
                        What is this service about?
                    </AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">
                            This service helps you manage your projects more efficiently by offering real-time collaboration, task tracking, and powerful analytics. Whether you're working solo or in a team, it's built to scale with your needs.
                        </p>
                    </AccordionContent>
                </AccordionPanel>
                <AccordionPanel value="2">
                    <AccordionHeader>
                        <template #toggleicon="{ active }">
                            <Minus v-if="active" />
                            <Plus v-else />
                        </template>
                        Is my data secure?
                    </AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">Yes. We use end-to-end encryption and follow industry best practices to ensure your data is protected. Your information is stored on secure servers and regularly backed up.</p>
                    </AccordionContent>
                </AccordionPanel>
                <AccordionPanel value="3">
                    <AccordionHeader>
                        <template #toggleicon="{ active }">
                            <Minus v-if="active" />
                            <Plus v-else />
                        </template>
                        Can I upgrade or downgrade my plan later?
                    </AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">Absolutely. You can change your subscription plan at any time from your account settings. Changes take effect immediately, and any billing adjustments are handled automatically.</p>
                    </AccordionContent>
                </AccordionPanel>
            </Accordion>
        </div>

        <div>
            <h3 class="text-sm! font-medium! text-surface-500! mb-2">CSS-only with data attributes</h3>
            <Accordion class="max-w-md mx-auto">
                <AccordionPanel value="1">
                    <AccordionHeader>
                        <template #toggleicon>
                            <ChevronDown class="transition-transform duration-200 in-data-[p=active]:rotate-180" />
                        </template>
                        What is this service about?
                    </AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">
                            This service helps you manage your projects more efficiently by offering real-time collaboration, task tracking, and powerful analytics. Whether you're working solo or in a team, it's built to scale with your needs.
                        </p>
                    </AccordionContent>
                </AccordionPanel>
                <AccordionPanel value="2">
                    <AccordionHeader>
                        <template #toggleicon>
                            <ChevronDown class="transition-transform duration-200 in-data-[p=active]:rotate-180" />
                        </template>
                        Is my data secure?
                    </AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">Yes. We use end-to-end encryption and follow industry best practices to ensure your data is protected. Your information is stored on secure servers and regularly backed up.</p>
                    </AccordionContent>
                </AccordionPanel>
            </Accordion>
        </div>
    </div>
</template>

<script setup>
import ChevronDown from '@primeicons/vue/chevron-down';
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';
<\/script>
```

## Disabled

Set disabled on an AccordionPanel to prevent user interaction with that panel.

```vue
<template>
    <div class="flex justify-center">
        <div class="w-full max-w-md space-y-8">
            <Accordion>
                <AccordionPanel value="0" disabled>
                    <AccordionHeader>How do I reset my password?</AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">You can reset your password by clicking the "Forgot password?" link on the login page. We'll send a password reset link to your registered email address.</p>
                    </AccordionContent>
                </AccordionPanel>
                <AccordionPanel value="1" disabled>
                    <AccordionHeader>Do you offer team accounts?</AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">Yes. Our Team and Business plans are designed for collaboration. You can invite team members, assign roles, and manage permissions easily from your dashboard.</p>
                    </AccordionContent>
                </AccordionPanel>
            </Accordion>
            <Accordion>
                <AccordionPanel value="0">
                    <AccordionHeader>What happens if I exceed my usage limit?</AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">If you go over your plan limits (e.g., storage or API requests), you'll receive a notification. You can either upgrade your plan or wait until the next billing cycle resets.</p>
                    </AccordionContent>
                </AccordionPanel>
                <AccordionPanel value="1" disabled>
                    <AccordionHeader>Is there a mobile app available?</AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-sm">Yes, we offer both iOS and Android apps so you can manage your account and stay connected on the go.</p>
                    </AccordionContent>
                </AccordionPanel>
            </Accordion>
        </div>
    </div>
</template>
```

## Template

Create accordion panels dynamically by iterating over a data source to keep structure consistent and reusable.

```vue
<template>
    <div class="flex justify-center">
        <Accordion class="w-full max-w-md">
            <AccordionPanel value="0">
                <AccordionHeader>
                    <template #toggleicon="{ active }">
                        <Minus v-if="active" />
                        <Plus v-else />
                    </template>
                    <span class="flex items-center gap-4">
                        <QuestionCircle class="text-yellow-500" />
                        <span class="font-medium">What is this service about?</span>
                    </span>
                </AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">
                        This service helps you manage your projects more efficiently by offering real-time collaboration, task tracking, and powerful analytics. Whether you're working solo or in a team, it's built to scale with your needs.
                    </p>
                </AccordionContent>
            </AccordionPanel>
            <AccordionPanel value="1">
                <AccordionHeader>
                    <template #toggleicon="{ active }">
                        <Minus v-if="active" />
                        <Plus v-else />
                    </template>
                    <span class="flex items-center gap-4">
                        <Lock class="text-blue-500" />
                        <span class="font-medium">Is my data secure?</span>
                    </span>
                </AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">Yes. We use end-to-end encryption and follow industry best practices to ensure your data is protected. Your information is stored on secure servers and regularly backed up.</p>
                </AccordionContent>
            </AccordionPanel>
            <AccordionPanel value="2">
                <AccordionHeader>
                    <template #toggleicon="{ active }">
                        <Minus v-if="active" />
                        <Plus v-else />
                    </template>
                    <span class="flex items-center gap-4">
                        <CreditCard class="text-green-500" />
                        <span class="font-medium">Can I upgrade or downgrade my plan later?</span>
                    </span>
                </AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">Absolutely. You can change your subscription plan at any time from your account settings. Changes take effect immediately, and any billing adjustments are handled automatically.</p>
                </AccordionContent>
            </AccordionPanel>
        </Accordion>
    </div>
</template>

<script setup>
import CreditCard from '@primeicons/vue/credit-card';
import Lock from '@primeicons/vue/lock';
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';
import QuestionCircle from '@primeicons/vue/question-circle';
<\/script>
```

## With RadioButton

RadioButton component can be used to group multiple AccordionPanel components.

```vue
<template>
    <div class="flex justify-center">
        <div class="w-full max-w-sm">
            <Accordion v-model:value="selected" class="w-full block border border-surface-200 dark:border-surface-700 rounded-md divide-y divide-surface-200 dark:divide-surface-700">
                <AccordionPanel v-for="item in items" :key="item.value" :value="item.value">
                    <AccordionHeader>
                        <template #toggleicon>
                            <span></span>
                        </template>
                        <span class="flex items-center gap-3 w-full">
                            <RadioButton v-model="selected" :value="item.value" />
                            <span class="flex items-center justify-between flex-1">
                                <span class="font-semibold text-base">{{ item.label }}</span>
                                <span class="font-semibold text-base">{{ item.price }}</span>
                            </span>
                        </span>
                    </AccordionHeader>
                    <AccordionContent>
                        <p class="m-0 text-surface-500 pl-8">{{ item.description }}</p>
                    </AccordionContent>
                </AccordionPanel>
            </Accordion>
            <Button class="w-full mt-4" size="large">{{ \`Buy Now for \${selectedPrice}\` }}</Button>
        </div>
    </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const items = ref([
    {
        label: 'Starter Plan',
        description: 'Perfect for individuals getting started. Includes access to core components and community support.',
        value: '0',
        price: '$99'
    },
    {
        label: 'Growth Plan',
        description: 'Ideal for freelancers and small teams. Unlocks advanced UI components and priority email support.',
        value: '1',
        price: '$249'
    },
    {
        label: 'Scale Plan',
        description: 'Best for growing businesses. Includes all features, early access to new releases, and Slack/Jira support.',
        value: '2',
        price: '$499'
    }
]);
const selected = ref('0');
const selectedPrice = computed(() => items.value.find((item) => item.value === selected.value)?.price ?? '');
<\/script>
```

## Dynamic

AccordionPanel can be generated dynamically using the standard v-for directive.

```vue
<template>
    <div>
        <Accordion v-model:value="active">
            <AccordionPanel v-for="tab in tabs" :key="tab.title" :value="tab.value">
                <AccordionHeader>{{ tab.title }}</AccordionHeader>
                <AccordionContent>
                    <p class="m-0 text-sm">{{ tab.content }}</p>
                </AccordionContent>
            </AccordionPanel>
        </Accordion>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const active = ref(['0']);
const tabs = ref([
    { title: 'Title 1', content: 'Content 1', value: '0' },
    { title: 'Title 2', content: 'Content 2', value: '1' },
    { title: 'Title 3', content: 'Content 3', value: '2' }
]);
<\/script>
```

## Accessibility

Screen Reader Accordion header elements have a button role and use aria-controls to define the id of the content section along with aria-expanded for the visibility state. The value to read a header element defaults to the value of the header property and can be customized by defining an aria-label or aria-labelledby property. Each header has a heading role, for which the level is customized by headerAriaLevel and has a default level of 2 as per W3C specifications. Disabled accordions headers use aria-disabled and are excluded from the keyboard navigation. The content uses region role, defines an id that matches the aria-controls of the header and aria-labelledby referring to the id of the header. Header Keyboard Support Key Function tab Moves focus to the next the focusable element in the page tab sequence. shift + tab Moves focus to the previous the focusable element in the page tab sequence. enter Toggles the visibility of the content. space Toggles the visibility of the content. down arrow Moves focus to the next header. up arrow Moves focus to the previous header. home Moves focus to the first header. end Moves focus to the last header.

## Accordion API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | null \| string \| number \| string[] \| number[] | null | Value of the active panel or an array of values in multiple mode. |
| multiple | boolean | false | When enabled, multiple tabs can be activated at the same time. |
| lazy | boolean | false | When enabled, hidden tabs are not rendered at all. Defaults to false that hides tabs with css. |
| expandIcon | string | - | Icon of a collapsed tab. |
| collapseIcon | string | - | Icon of an expanded tab. |
| tabindex | number | 0 | Index of the element in tabbing order. |
| selectOnFocus | boolean | false | When enabled, the focused tab is activated. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | AccordionPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-accordion | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| accordion.transition.duration | --p-accordion-transition-duration | Transition duration of root |
| accordion.panel.border.width | --p-accordion-panel-border-width | Border width of panel |
| accordion.panel.border.color | --p-accordion-panel-border-color | Border color of panel |
| accordion.header.color | --p-accordion-header-color | Color of header |
| accordion.header.hover.color | --p-accordion-header-hover-color | Hover color of header |
| accordion.header.active.color | --p-accordion-header-active-color | Active color of header |
| accordion.header.active.hover.color | --p-accordion-header-active-hover-color | Active hover color of header |
| accordion.header.padding | --p-accordion-header-padding | Padding of header |
| accordion.header.font.weight | --p-accordion-header-font-weight | Font weight of header |
| accordion.header.font.size | --p-accordion-header-font-size | Font size of header |
| accordion.header.border.radius | --p-accordion-header-border-radius | Border radius of header |
| accordion.header.border.width | --p-accordion-header-border-width | Border width of header |
| accordion.header.border.color | --p-accordion-header-border-color | Border color of header |
| accordion.header.background | --p-accordion-header-background | Background of header |
| accordion.header.hover.background | --p-accordion-header-hover-background | Hover background of header |
| accordion.header.active.background | --p-accordion-header-active-background | Active background of header |
| accordion.header.active.hover.background | --p-accordion-header-active-hover-background | Active hover background of header |
| accordion.header.focus.ring.width | --p-accordion-header-focus-ring-width | Focus ring width of header |
| accordion.header.focus.ring.style | --p-accordion-header-focus-ring-style | Focus ring style of header |
| accordion.header.focus.ring.color | --p-accordion-header-focus-ring-color | Focus ring color of header |
| accordion.header.focus.ring.offset | --p-accordion-header-focus-ring-offset | Focus ring offset of header |
| accordion.header.focus.ring.shadow | --p-accordion-header-focus-ring-shadow | Focus ring shadow of header |
| accordion.header.toggle.icon.color | --p-accordion-header-toggle-icon-color | Toggle icon color of header |
| accordion.header.toggle.icon.hover.color | --p-accordion-header-toggle-icon-hover-color | Toggle icon hover color of header |
| accordion.header.toggle.icon.active.color | --p-accordion-header-toggle-icon-active-color | Toggle icon active color of header |
| accordion.header.toggle.icon.active.hover.color | --p-accordion-header-toggle-icon-active-hover-color | Toggle icon active hover color of header |
| accordion.header.first.top.border.radius | --p-accordion-header-first-top-border-radius | First top border radius of header |
| accordion.header.first.border.width | --p-accordion-header-first-border-width | First border width of header |
| accordion.header.last.bottom.border.radius | --p-accordion-header-last-bottom-border-radius | Last bottom border radius of header |
| accordion.header.last.active.bottom.border.radius | --p-accordion-header-last-active-bottom-border-radius | Last active bottom border radius of header |
| accordion.content.border.width | --p-accordion-content-border-width | Border width of content |
| accordion.content.border.color | --p-accordion-content-border-color | Border color of content |
| accordion.content.background | --p-accordion-content-background | Background of content |
| accordion.content.color | --p-accordion-content-color | Color of content |
| accordion.content.padding | --p-accordion-content-padding | Padding of content |

## Accordion Panel API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | undefined \| string \| number | - | Unique value of item. |
| disabled | boolean | false | Whether the item is disabled. |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | AccordionPanelPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-accordionpanel | Class name of the root element |

## Accordion Header API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | AccordionHeaderPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| toggleicon | AccordionHeaderPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-accordionheader | Class name of the root element |
| p-accordionheader-toggle-icon | Class name of the toggleicon element |

## Accordion Content API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | AccordionContentPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| transition | AccordionContentPassThroughOptionType | Used to pass attributes to the transition's DOM element. |
| contentWrapper | AccordionContentPassThroughOptionType | Used to pass attributes to the content's wrapper DOM element. |
| content | AccordionContentPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-accordioncontent | Class name of the root element |
| p-accordioncontent-content | Class name of the content element |
