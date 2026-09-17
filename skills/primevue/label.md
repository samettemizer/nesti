# Label

Label provides accessible text labels for form controls. Use the for attribute to link the label to a form control by its id.

## Basic

An accessible label element associated with a form control.

```vue
<template>
    <div class="flex flex-wrap justify-center">
        <div class="flex flex-col gap-2 w-full max-w-sm">
            <Label for="username">Username</Label>
            <InputText id="username" v-model="value" placeholder="Enter username" />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Required

You can display required indicators in the label content while keeping the input semantics with required or aria-required .

```vue
<template>
    <div class="flex flex-wrap justify-center">
        <div class="flex flex-col gap-2 w-full max-w-sm">
            <Label for="email" class="font-medium!">
                <Envelope />
                <span>Email</span>
                <span aria-hidden="true">*</span>
            </Label>
            <InputText id="email" v-model="value" type="email" placeholder="name@example.com" required aria-required="true" />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Envelope from '@primeicons/vue/envelope';

const value = ref('');
<\/script>
```

## Wrapper

Label can wrap a form control to associate them implicitly without for . Useful for card-style selectable options.

```vue
<template>
    <div class="flex flex-wrap justify-center">
        <div class="flex flex-col w-full max-w-3xs gap-2">
            <Label v-for="plan in plans" :key="plan.id" :class="'flex items-start gap-3 p-3 rounded-md border cursor-pointer ' + (selected === plan.id ? 'border-primary' : 'border-surface')">
                <RadioButton name="plan" :value="plan.id" v-model="selected" />
                <div class="flex flex-col gap-0.5">
                    <span class="font-medium">{{ plan.name }}</span>
                    <span class="text-xs text-surface-500">{{ plan.description }}</span>
                </div>
            </Label>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selected = ref('pro');
const plans = ref([
    { id: 'starter', name: 'Starter', description: 'For solo developers.' },
    { id: 'pro', name: 'Pro', description: 'For growing teams.' },
    { id: 'enterprise', name: 'Enterprise', description: 'For large organizations.' }
]);
<\/script>
```

## Disabled

Label reflects the disabled state of an associated control automatically when the control and label are peers or when the container has data-disabled .

```vue
<template>
    <div class="flex flex-col items-start max-w-3xs w-full mx-auto gap-6">
        <div class="flex flex-col gap-2 w-full">
            <Label for="account-id">Account ID</Label>
            <InputText id="account-id" v-model="accountId" disabled />
        </div>
        <div data-disabled="true" class="flex flex-col gap-2 w-full">
            <Label for="api-key">API Key</Label>
            <span>
                <InputText id="api-key" v-model="apiKey" disabled fluid />
            </span>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const accountId = ref('ACC-2026-0042');
const apiKey = ref('sk_live_***************');
<\/script>
```

## Accessibility

Screen Reader Label renders a native label element. Use the for attribute to associate it with a form control id, or wrap the form control inside the label. Keyboard Support Component does not include any interactive elements.

## Label API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | LABEL | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | LabelPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-label | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| label.gap | --p-label-gap | Gap of root |
| label.font.size | --p-label-font-size | Font size of root |
| label.font.weight | --p-label-font-weight | Font weight of root |
| label.text.color | --p-label-text-color | Text color of root |
| label.disabled.opacity | --p-label-disabled-opacity | Disabled opacity of root |
