# RadioButton

RadioButton is an extension to standard radio button element with theming.

## Basic

Selects a single option from a group of mutually exclusive choices.

```vue
<template>
    <div class="flex items-center justify-center">
        <div class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
                <RadioButton v-model="ingredient" inputId="ingredient-strawberry" name="fruit" value="strawberry" />
                <Label for="ingredient-strawberry" class="text-sm!">🍓 Strawberry</Label>
            </div>
            <div class="flex items-center gap-3">
                <RadioButton v-model="ingredient" inputId="ingredient-banana" name="fruit" value="banana" />
                <Label for="ingredient-banana" class="text-sm!">🍌 Banana</Label>
            </div>
            <div class="flex items-center gap-3">
                <RadioButton v-model="ingredient" inputId="ingredient-watermelon" name="fruit" value="watermelon" />
                <Label for="ingredient-watermelon" class="text-sm!">🍉 Watermelon</Label>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const ingredient = ref(null);
<\/script>
```

## Group

RadioButton is used as a controlled input with value and v-model properties.

```vue
<template>
    <div class="flex justify-center">
        <div class="flex flex-wrap gap-4">
            <div class="flex items-center">
                <RadioButton v-model="ingredient" inputId="ingredient1" name="pizza" value="Cheese" />
                <Label for="ingredient1" class="text-sm! ml-2">Cheese</Label>
            </div>
            <div class="flex items-center">
                <RadioButton v-model="ingredient" inputId="ingredient2" name="pizza" value="Mushroom" />
                <Label for="ingredient2" class="text-sm! ml-2">Mushroom</Label>
            </div>
            <div class="flex items-center">
                <RadioButton v-model="ingredient" inputId="ingredient3" name="pizza" value="Pepper" />
                <Label for="ingredient3" class="text-sm! ml-2">Pepper</Label>
            </div>
            <div class="flex items-center">
                <RadioButton v-model="ingredient" inputId="ingredient4" name="pizza" value="Onion" />
                <Label for="ingredient4" class="text-sm! ml-2">Onion</Label>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const ingredient = ref(null);
<\/script>
```

## Dynamic

RadioButtons can be generated using a list of values.

```vue
<template>
    <div class="flex justify-center">
        <div class="flex flex-wrap gap-4">
            <div v-for="category in categories" :key="category.key" class="flex items-center gap-2">
                <RadioButton v-model="selectedCategory" :inputId="category.key" name="category" :value="category.key" />
                <Label :for="category.key" class="text-sm!">{{ category.name }}</Label>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedCategory = ref(null);
const categories = ref([
    { name: 'Accounting', key: 'A' },
    { name: 'Marketing', key: 'M' },
    { name: 'Production', key: 'P' },
    { name: 'Research', key: 'R' }
]);
<\/script>
```

## Card

RadioButtons can be displayed in a card style.

```vue
<template>
    <div class="max-w-xs mx-auto">
        <span class="font-medium">Choose a plan:</span>
        <div class="mt-2 flex flex-col gap-3">
            <label
                v-for="plan in plans"
                :key="plan.id"
                :for="'plan-' + plan.id"
                :class="'flex-1 flex items-start gap-2 p-3 rounded-lg border hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors cursor-pointer ' + (selectedPlan === plan.id ? 'border-primary' : 'border-surface')"
            >
                <div class="flex-1 flex flex-col gap-1">
                    <div class="flex items-center justify-between gap-2">
                        <div class="flex items-center gap-2">
                            <span class="font-medium leading-none">{{ plan.name }}</span>
                            <Tag v-if="plan.tag" :value="plan.tag" />
                        </div>
                        <div class="text-sm text-color">
                            <span class="font-semibold">{{ plan.price }}</span>
                            <span class="text-surface-500">{{ plan.period }}</span>
                        </div>
                    </div>
                    <span class="text-sm text-surface-500">{{ plan.description }}</span>
                </div>
                <RadioButton v-model="selectedPlan" :inputId="'plan-' + plan.id" name="plan" :value="plan.id" />
            </label>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedPlan = ref('pro');
const plans = ref([
    { id: 'starter', name: 'Starter', price: '$0', period: '/month', description: 'For solo developers exploring the platform.', tag: null },
    { id: 'pro', name: 'Pro', price: '$29', period: '/month', description: 'For growing teams shipping in production.', tag: 'Popular' },
    { id: 'enterprise', name: 'Enterprise', price: 'Custom', period: '', description: 'For large organizations with custom needs.', tag: null }
]);
<\/script>
```

## Sizes

RadioButton provides small and large sizes as alternatives to the base.

```vue
<template>
    <div class="flex justify-center">
        <div class="flex flex-wrap gap-4">
            <div class="flex items-center gap-2">
                <RadioButton v-model="size" inputId="size_small" name="size" value="Small" size="small" />
                <Label for="size_small" class="text-sm!">Small</Label>
            </div>
            <div class="flex items-center gap-2">
                <RadioButton v-model="size" inputId="size_normal" name="size" value="Normal" />
                <Label for="size_normal">Normal</Label>
            </div>
            <div class="flex items-center gap-2">
                <RadioButton v-model="size" inputId="size_large" name="size" value="Large" size="large" />
                <Label for="size_large" class="text-lg!">Large</Label>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const size = ref('Normal');
<\/script>
```

## Filled

Specify the variant property as filled to display the component with a higher visual emphasis than the default outlined style.

```vue
<template>
    <div class="flex justify-center">
        <RadioButton v-model="checked" variant="filled" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(false);
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused.

```vue
<template>
    <div class="flex justify-center gap-2">
        <RadioButton v-model="value" :value="1" disabled />
        <RadioButton v-model="value" :value="2" disabled />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(2);
<\/script>
```

## Invalid

The invalid state is applied using the invalid property to indicate failed validation, which can be integrated with form validation libraries.

```vue
<template>
    <div class="flex justify-center">
        <RadioButton v-model="value" :invalid="!value" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(false);
<\/script>
```

## Forms

RadioButton integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4">
            <div class="flex flex-col gap-2">
                <RadioButtonGroup name="ingredient" class="flex flex-wrap gap-4">
                    <div class="flex items-center gap-2">
                        <RadioButton inputId="cheese" value="Cheese" />
                        <Label for="cheese">Cheese</Label>
                    </div>
                    <div class="flex items-center gap-2">
                        <RadioButton inputId="mushroom" value="Mushroom" />
                        <Label for="mushroom">Mushroom</Label>
                    </div>
                    <div class="flex items-center gap-2">
                        <RadioButton inputId="pepper" value="Pepper" />
                        <Label for="pepper">Pepper</Label>
                    </div>
                    <div class="flex items-center gap-2">
                        <RadioButton inputId="onion" value="Onion" />
                        <Label for="onion">Onion</Label>
                    </div>
                </RadioButtonGroup>
                <Message v-if="$form.ingredient?.invalid" severity="error" size="small" variant="simple">{{ $form.ingredient.error?.message }}</Message>
            </div>
            <Button type="submit" severity="secondary">Submit</Button>
        </Form>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from "primevue/usetoast";
import { z } from 'zod';

const toast = useToast();
const initialValues = ref({
    ingredient: ''
});
const resolver = ref(zodResolver(
    z.object({
        ingredient: z.string().min(1, { message: 'Ingredient is required.' })
    })
));

const onFormSubmit = ({ valid }) => {
    if (valid) {
        toast.add({ severity: 'success', summary: 'Form is submitted.', life: 3000 });
    }
};
<\/script>
```

## Accessibility

Screen Reader RadioButton component uses a hidden native radio button element internally that is only visible to screen readers. Value to describe the component can either be provided via label tag combined with id prop or using aria-labelledby , aria-label props. Keyboard Support Key Function tab Moves focus to the checked radio button, if there is none within the group then first radio button receives the focus. left arrow up arrow Moves focus to the previous radio button, if there is none then last radio button receives the focus. right arrow down arrow Moves focus to the next radio button, if there is none then first radio button receives the focus. space If the focused radio button is unchecked, changes the state to checked.

```vue
<template>
    <label for="rb1">One</label>
    <RadioButton inputId="rb1" />

    <span id="rb2">Two</span>
    <RadioButton aria-labelledby="rb2" />

    <RadioButton aria-label="Three" />
</template>
```

## Radio Button API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | any | - | Value of the checkbox. |
| modelValue | any | - | Value binding of the checkbox. |
| defaultValue | any | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | Name of the input element. |
| binary | boolean | - | Allows to select a boolean value. |
| size | any | - | Defines the size of the component. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| variant | any | null | Specifies the input variant of the component. |
| readonly | boolean | - | When present, it specifies that an input field is read-only. |
| tabindex | number | - | Index of the element in tabbing order. |
| inputId | string | - | Identifier of the underlying input element. |
| inputStyle | object | - | Inline style of the input field. |
| inputClass | string \| object | - | Style class of the input field. |
| ariaLabelledby | string | - | Establishes relationships between the component and label(s) where its value should be one or more element IDs. |
| ariaLabel | string | - | Establishes a string value that labels the component. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | RadioButtonPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| input | RadioButtonPassThroughOptionType | Used to pass attributes to the input's DOM element. |
| box | RadioButtonPassThroughOptionType | Used to pass attributes to the box's DOM element. |
| icon | RadioButtonPassThroughOptionType | Used to pass attributes to the icon's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-radiobutton | Class name of the root element |
| p-radiobutton-box | Class name of the box element |
| p-radiobutton-input | Class name of the input element |
| p-radiobutton-icon | Class name of the icon element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| radiobutton.width | --p-radiobutton-width | Width of root |
| radiobutton.height | --p-radiobutton-height | Height of root |
| radiobutton.background | --p-radiobutton-background | Background of root |
| radiobutton.checked.background | --p-radiobutton-checked-background | Checked background of root |
| radiobutton.checked.hover.background | --p-radiobutton-checked-hover-background | Checked hover background of root |
| radiobutton.disabled.background | --p-radiobutton-disabled-background | Disabled background of root |
| radiobutton.filled.background | --p-radiobutton-filled-background | Filled background of root |
| radiobutton.border.color | --p-radiobutton-border-color | Border color of root |
| radiobutton.hover.border.color | --p-radiobutton-hover-border-color | Hover border color of root |
| radiobutton.focus.border.color | --p-radiobutton-focus-border-color | Focus border color of root |
| radiobutton.checked.border.color | --p-radiobutton-checked-border-color | Checked border color of root |
| radiobutton.checked.hover.border.color | --p-radiobutton-checked-hover-border-color | Checked hover border color of root |
| radiobutton.checked.focus.border.color | --p-radiobutton-checked-focus-border-color | Checked focus border color of root |
| radiobutton.checked.disabled.border.color | --p-radiobutton-checked-disabled-border-color | Checked disabled border color of root |
| radiobutton.invalid.border.color | --p-radiobutton-invalid-border-color | Invalid border color of root |
| radiobutton.shadow | --p-radiobutton-shadow | Shadow of root |
| radiobutton.focus.ring.width | --p-radiobutton-focus-ring-width | Focus ring width of root |
| radiobutton.focus.ring.style | --p-radiobutton-focus-ring-style | Focus ring style of root |
| radiobutton.focus.ring.color | --p-radiobutton-focus-ring-color | Focus ring color of root |
| radiobutton.focus.ring.offset | --p-radiobutton-focus-ring-offset | Focus ring offset of root |
| radiobutton.focus.ring.shadow | --p-radiobutton-focus-ring-shadow | Focus ring shadow of root |
| radiobutton.transition.duration | --p-radiobutton-transition-duration | Transition duration of root |
| radiobutton.sm.width | --p-radiobutton-sm-width | Sm width of root |
| radiobutton.sm.height | --p-radiobutton-sm-height | Sm height of root |
| radiobutton.lg.width | --p-radiobutton-lg-width | Lg width of root |
| radiobutton.lg.height | --p-radiobutton-lg-height | Lg height of root |
| radiobutton.icon.size | --p-radiobutton-icon-size | Size of icon |
| radiobutton.icon.checked.color | --p-radiobutton-icon-checked-color | Checked color of icon |
| radiobutton.icon.checked.hover.color | --p-radiobutton-icon-checked-hover-color | Checked hover color of icon |
| radiobutton.icon.disabled.color | --p-radiobutton-icon-disabled-color | Disabled color of icon |
| radiobutton.icon.sm.size | --p-radiobutton-icon-sm-size | Sm size of icon |
| radiobutton.icon.lg.size | --p-radiobutton-icon-lg-size | Lg size of icon |

## Radio Button Group API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | any | - | Value binding of the radiobuttons. |
| defaultValue | any | - | Default values of the radiobuttons in uncontrolled mode. |
| name | string | - | Name of the input elements. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| formControl | any | - | Used to set form control options. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Slots

| Name |Parameters |Description |
| --- | --- | --- |
| default | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | RadioButtonGroupPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-radiobutton-group | Class name of the root element |
