# Checkbox

Checkbox is an extension to standard checkbox element with theming.

## Basic

Binary checkbox is used as a controlled input with v-model and binary properties.

```vue
<template>
    <div class="flex justify-center gap-4">
        <Checkbox v-model="checked" binary />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(false);
<\/script>
```

## Indicator

Use the icon template to customize the visual indicator inside the checkbox.

```vue
<template>
    <div class="flex items-center justify-center">
        <div class="flex items-center gap-2">
            <Checkbox v-model="checked" binary indeterminate inputId="checkbox-indicator" @change="onCheck">
                <template #icon="{ checked, class: iconClass }">
                    <Check v-if="checked" :class="iconClass" />
                    <Times v-else :class="iconClass" />
                </template>
            </Checkbox>
            <Label for="checkbox-indicator" class="text-sm">Select all notifications</Label>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Check from '@primeicons/vue/check';
import Minus from '@primeicons/vue/minus';
import Times from '@primeicons/vue/times';

const checked = ref(false);
const isIndeterminate = ref(true);

const onCheck = () => {
    isIndeterminate.value = false;
};
<\/script>
```

## Indeterminate

The indeterminate state indicates that a checkbox is neither "on" or "off".

```vue
<template>
    <div class="flex items-center gap-2 justify-center">
        <Checkbox v-model="checked" binary indeterminate inputId="indeterminate-checkbox" />
        <Label for="indeterminate-checkbox" class="text-sm">Email Notifications</Label>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(false);
<\/script>
```

## Dynamic

Checkboxes can be generated using a list of values.

```vue
<template>
    <div class="flex justify-center">
        <div class="flex flex-col gap-4">
            <div v-for="category of categories" :key="category.key" class="flex items-center gap-2">
                <Checkbox v-model="selectedCategories" :inputId="category.key" name="group" :value="category" />
                <Label :for="category.key" class="text-sm">{{ category.name }}</Label>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const categories = ref([
    { name: 'Accounting', key: 'A' },
    { name: 'Marketing', key: 'M' },
    { name: 'Production', key: 'P' },
    { name: 'Research', key: 'R' }
]);
const selectedCategories = ref([categories.value[1]]);
<\/script>
```

## Sizes

Checkbox provides small and large sizes as alternatives to the base.

```vue
<template>
    <div class="flex flex-wrap items-center justify-center gap-4">
        <div class="flex items-center gap-2">
            <Checkbox v-model="small" binary inputId="small-checkbox" size="small" />
            <Label for="small-checkbox" class="text-sm">Small</Label>
        </div>
        <div class="flex items-center gap-2">
            <Checkbox v-model="normal" binary inputId="normal-checkbox" />
            <Label for="normal-checkbox" class="text-sm">Normal</Label>
        </div>
        <div class="flex items-center gap-2">
            <Checkbox v-model="large" binary inputId="large-checkbox" size="large" />
            <Label for="large-checkbox" class="text-sm">Large</Label>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const small = ref(false);
const normal = ref(false);
const large = ref(false);
<\/script>
```

## Filled

Specify the variant property as filled to display the component with a higher visual emphasis than the default outlined style.

```vue
<template>
    <div class="flex items-center justify-center">
        <div class="flex items-center gap-2">
            <Checkbox v-model="checked" binary variant="filled" inputId="filled-checkbox" />
            <Label for="filled-checkbox" class="text-sm">Filled</Label>
        </div>
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
    <div class="flex items-center justify-center gap-4">
        <Checkbox v-model="checked1" binary disabled />
        <Checkbox v-model="checked2" binary disabled />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked1 = ref(false);
const checked2 = ref(true);
<\/script>
```

## Invalid

The invalid state is applied using the invalid property to indicate failed validation, which can be integrated with form validation libraries.

```vue
<template>
    <div class="flex items-center justify-center">
        <div class="flex items-center gap-2">
            <Checkbox v-model="checked" binary :invalid="!checked" inputId="invalid-checkbox" />
            <Label for="invalid-checkbox" :class="['transition-colors', { 'text-red-500! dark:text-red-400!': !checked }]">Invalid</Label>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(false);
<\/script>
```

## Forms

Checkbox integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex justify-center flex-col gap-4">
            <div class="flex flex-col gap-2">
                <CheckboxGroup name="ingredient" class="flex flex-wrap gap-4">
                    <div class="flex items-center gap-2">
                        <Checkbox inputId="cheese" value="Cheese" />
                        <Label for="cheese"> Cheese </Label>
                    </div>
                    <div class="flex items-center gap-2">
                        <Checkbox inputId="mushroom" value="Mushroom" />
                        <Label for="mushroom"> Mushroom </Label>
                    </div>
                    <div class="flex items-center gap-2">
                        <Checkbox inputId="pepper" value="Pepper" />
                        <Label for="pepper"> Pepper </Label>
                    </div>
                    <div class="flex items-center gap-2">
                        <Checkbox inputId="onion" value="Onion" />
                        <Label for="onion"> Onion </Label>
                    </div>
                </CheckboxGroup>
                <Message v-if="$form.ingredient?.invalid" severity="error" size="small" variant="simple">{{ $form.ingredient.error?.message }}</Message>
            </div>
            <Button type="submit" severity="secondary">Submit</Button>
        </Form>
    </div>
    <Toast />
</template>

<script setup>
import { ref } from 'vue';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from "primevue/usetoast";
import { z } from 'zod';

const toast = useToast();
const initialValues = ref({
    ingredient: []
});
const resolver = ref(zodResolver(
    z.object({
        ingredient: z.array(z.string()).min(1, { message: 'At least one ingredient must be selected.' })
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

Screen Reader Checkbox component uses a hidden native checkbox element internally that is only visible to screen readers. Value to describe the component can either be provided via label tag combined with inputId prop or using aria-labelledby , aria-label props. Keyboard Support Key Function tab Moves focus to the checkbox. space Toggles the checked state.

```vue
<template>
    <label for="chkbox1">Remember Me</label>
    <Checkbox inputId="chkbox1" />

    <span id="chkbox2">Remember Me</span>
    <Checkbox aria-labelledby="chkbox2" />

    <Checkbox aria-label="Remember Me" />
</template>
```

## Checkbox API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | any | - | Value of the checkbox. |
| modelValue | any | - | Value binding of the checkbox. |
| defaultValue | any | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | Name of the input element. |
| binary | boolean | - | Allows to select a boolean value instead of multiple values. |
| indeterminate | boolean | - | When present, it specifies input state as indeterminate. |
| size | "small" \| "large" | - | Defines the size of the component. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | - | When present, it specifies that the element should be disabled. |
| variant | any | null | Specifies the input variant of the component. |
| readonly | boolean | - | When present, it specifies that an input field is read-only. |
| required | boolean | - | When present, it specifies that the element is required. |
| tabindex | number | - | Index of the element in tabbing order. |
| trueValue | any | - | Value in checked state. |
| falseValue | any | - | Value in unchecked state. |
| inputId | string | - | Identifier of the underlying input element. |
| inputClass | object | - | Style class of the input field. |
| inputStyle | string \| object | - | Inline style of the input field. |
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
| root | CheckboxPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| input | CheckboxPassThroughOptionType | Used to pass attributes to the input's DOM element. |
| box | CheckboxPassThroughOptionType | Used to pass attributes to the box's DOM element. |
| indicator | CheckboxPassThroughOptionType | Used to pass attributes to the indicator's DOM element. |
| icon | CheckboxPassThroughOptionType | Used to pass attributes to the icon's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-checkbox | Class name of the root element |
| p-checkbox-box | Class name of the box element |
| p-checkbox-input | Class name of the input element |
| p-checkbox-icon | Class name of the icon element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| checkbox.border.radius | --p-checkbox-border-radius | Border radius of root |
| checkbox.width | --p-checkbox-width | Width of root |
| checkbox.height | --p-checkbox-height | Height of root |
| checkbox.background | --p-checkbox-background | Background of root |
| checkbox.checked.background | --p-checkbox-checked-background | Checked background of root |
| checkbox.checked.hover.background | --p-checkbox-checked-hover-background | Checked hover background of root |
| checkbox.disabled.background | --p-checkbox-disabled-background | Disabled background of root |
| checkbox.filled.background | --p-checkbox-filled-background | Filled background of root |
| checkbox.border.color | --p-checkbox-border-color | Border color of root |
| checkbox.hover.border.color | --p-checkbox-hover-border-color | Hover border color of root |
| checkbox.focus.border.color | --p-checkbox-focus-border-color | Focus border color of root |
| checkbox.checked.border.color | --p-checkbox-checked-border-color | Checked border color of root |
| checkbox.checked.hover.border.color | --p-checkbox-checked-hover-border-color | Checked hover border color of root |
| checkbox.checked.focus.border.color | --p-checkbox-checked-focus-border-color | Checked focus border color of root |
| checkbox.checked.disabled.border.color | --p-checkbox-checked-disabled-border-color | Checked disabled border color of root |
| checkbox.invalid.border.color | --p-checkbox-invalid-border-color | Invalid border color of root |
| checkbox.shadow | --p-checkbox-shadow | Shadow of root |
| checkbox.focus.ring.width | --p-checkbox-focus-ring-width | Focus ring width of root |
| checkbox.focus.ring.style | --p-checkbox-focus-ring-style | Focus ring style of root |
| checkbox.focus.ring.color | --p-checkbox-focus-ring-color | Focus ring color of root |
| checkbox.focus.ring.offset | --p-checkbox-focus-ring-offset | Focus ring offset of root |
| checkbox.focus.ring.shadow | --p-checkbox-focus-ring-shadow | Focus ring shadow of root |
| checkbox.transition.duration | --p-checkbox-transition-duration | Transition duration of root |
| checkbox.sm.width | --p-checkbox-sm-width | Sm width of root |
| checkbox.sm.height | --p-checkbox-sm-height | Sm height of root |
| checkbox.lg.width | --p-checkbox-lg-width | Lg width of root |
| checkbox.lg.height | --p-checkbox-lg-height | Lg height of root |
| checkbox.icon.size | --p-checkbox-icon-size | Size of icon |
| checkbox.icon.color | --p-checkbox-icon-color | Color of icon |
| checkbox.icon.checked.color | --p-checkbox-icon-checked-color | Checked color of icon |
| checkbox.icon.checked.hover.color | --p-checkbox-icon-checked-hover-color | Checked hover color of icon |
| checkbox.icon.disabled.color | --p-checkbox-icon-disabled-color | Disabled color of icon |
| checkbox.icon.sm.size | --p-checkbox-icon-sm-size | Sm size of icon |
| checkbox.icon.lg.size | --p-checkbox-icon-lg-size | Lg size of icon |

## Checkbox Group API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | any | - | Value binding of the checkboxes. |
| defaultValue | any | - | Default values of the checkboxes in uncontrolled mode. |
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
| root | CheckboxGroupPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-checkbox-group | Class name of the root element |
