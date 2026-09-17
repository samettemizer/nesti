# SelectButton

SelectButton is used to choose single or multiple items from a list using buttons.

## Basic

SelectButton requires a value to bind and a collection of options.

```vue
<template>
    <div class="flex justify-center">
        <SelectButton v-model="value" :options="stateOptions" optionLabel="label" optionValue="value" aria-labelledby="basic" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('one-way');
const stateOptions = ref([
    { label: 'One-Way', value: 'one-way' },
    { label: 'Return', value: 'return' }
]);
<\/script>
```

## Multiple

SelectButton allows selecting only one item by default and setting multiple option enables choosing more than one item. In multiple case, model property should be an array.

```vue
<template>
    <div class="flex justify-center">
        <SelectButton v-model="value" :options="paymentOptions" optionLabel="name" optionValue="value" multiple />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(null);
const paymentOptions = ref([
    { name: 'Option 1', value: 1 },
    { name: 'Option 2', value: 2 },
    { name: 'Option 3', value: 3 }
]);
<\/script>
```

## Template

For custom content support define an option template where the default slot props refer to an option.

```vue
<template>
    <div class="flex justify-center">
        <SelectButton v-model="value" :options="justifyOptions" optionLabel="justify">
            <template #option="{ icon }">
                <component :is="icon" />
            </template>
        </SelectButton>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import AlignCenter from '@primeicons/vue/align-center';
import AlignJustify from '@primeicons/vue/align-justify';
import AlignLeft from '@primeicons/vue/align-left';
import AlignRight from '@primeicons/vue/align-right';

const value = ref(null);
const justifyOptions = ref([
    { icon: AlignLeft, justify: 'Left' },
    { icon: AlignRight, justify: 'Right' },
    { icon: AlignCenter, justify: 'Center' },
    { icon: AlignJustify, justify: 'Justify' }
]);
<\/script>
```

## Sizes

SelectButton provides small and large sizes as alternatives to the base.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <SelectButton v-model="value1" :options="options" size="small" />
        <SelectButton v-model="value2" :options="options" />
        <SelectButton v-model="value3" :options="options" size="large" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(null);
const value2 = ref('Beginner');
const value3 = ref('Expert');
const options = ref(['Beginner', 'Expert']);
<\/script>
```

## Fluid

The fluid prop makes the component take up the full width of its container when set to true.

```vue
<template>
    <SelectButton v-model="value" :options="stateOptions" optionLabel="label" optionValue="value" fluid />
</template>

<script setup>
import { ref } from 'vue';

const value = ref('one-way');
const stateOptions = ref([
    { label: 'One-Way', value: 'one-way' },
    { label: 'Return', value: 'return' }
]);
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused entirely. Certain options can also be disabled using the optionDisabled property.

```vue
<template>
    <div class="flex justify-center flex-wrap gap-4">
        <SelectButton v-model="value1" :options="stateOptions" optionLabel="label" optionValue="value" disabled />
        <SelectButton v-model="value2" :options="stateOptions2" optionLabel="label" optionValue="value" optionDisabled="constant" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref('off');
const value2 = ref('Option 1');
const stateOptions = ref([
    { label: 'Off', value: 'off' },
    { label: 'On', value: 'on' }
]);
const stateOptions2 = ref([
    { label: 'Option 1', value: 'Option 1' },
    { label: 'Option 2', value: 'Option 2', constant: true }
]);
<\/script>
```

## Invalid

The invalid state is applied using the invalid property to indicate failed validation, which can be integrated with form validation libraries.

```vue
<template>
    <div class="flex justify-center">
        <SelectButton v-model="value" :options="stateOptions" optionLabel="label" optionValue="value" :invalid="value == null" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(undefined);
const stateOptions = ref([
    { label: 'One-Way', value: 'one-way' },
    { label: 'Return', value: 'return' }
]);
<\/script>
```

## Forms

SelectButton integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4">
            <div class="flex items-center flex-col gap-1">
                <SelectButton name="selection" :options="options" />
                <Message v-if="$form.selection?.invalid" severity="error" size="small" variant="simple">{{ $form.selection.error?.message }}</Message>
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
    selection: ''
});
const resolver = ref(zodResolver(
    z.object({
        selection: z.preprocess((val) => (val === null ? '' : val), z.string().min(1, { message: 'Selection is required' }))
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

Screen Reader The container element that wraps the buttons has a group role whereas each button element uses button role and aria-pressed is updated depending on selection state. Value to describe an option is automatically set using the ariaLabel property that refers to the label of an option so it is still suggested to define a label even the option display consists of presentational content like icons only. Keyboard Support Key Function tab Moves focus to the buttons. space Toggles the checked state of a button.

## Select Button API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | any | - | Value of the component. |
| defaultValue | any | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | The name attribute for the element, typically used in form submissions. |
| options | any[] | - | An array of selectitems to display as the available options. |
| optionLabel | string \| Function | - | Property name or getter function to use as the label of an option. |
| optionValue | string \| Function | - | Property name or getter function to use as the value of an option, defaults to the option itself when not defined. |
| optionDisabled | string \| Function | - | Property name or getter function to use as the disabled flag of an option, defaults to false when not defined. |
| multiple | boolean | false | When specified, allows selecting multiple values. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the element should be disabled. |
| fluid | boolean | null | Spans 100% width of the container when enabled. |
| dataKey | string | - | A property to uniquely identify an option. |
| allowEmpty | boolean | true | Whether selection can be cleared. |
| ariaLabelledby | string | - | Identifier of the underlying element. |
| size | any | - | Defines the size of the component. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SelectButtonPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| pcToggleButton | SelectButtonPassThroughOptionType | Used to pass attributes to the ToggleButton component. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-selectbutton | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| selectbutton.border.radius | --p-selectbutton-border-radius | Border radius of root |
| selectbutton.invalid.border.color | --p-selectbutton-invalid-border-color | Invalid border color of root |
