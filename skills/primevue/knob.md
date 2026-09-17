# Knob

Knob is a form component to define number inputs with a dial.

## Basic

Knob is an input component and used with the standard v-model directive.

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Min/Max

Boundaries are configured with the min and max properties whose defaults are 0 and 100 respectively.

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" :min="-50" :max="50" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(10);
<\/script>
```

## Step

Size of each movement is defined with the step property.

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" :step="10" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Template

Label is a string template that can be customized with the valueTemplate property having 60 as the placeholder .

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" valueTemplate="{value}%" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(60);
<\/script>
```

## Stroke

The border size is specified with the strokeWidth property as a number in pixels.

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" :strokeWidth="5" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(40);
<\/script>
```

## Size

Diameter of the knob is defined in pixels using the size property.

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" :size="200" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(60);
<\/script>
```

## Color

Colors are customized with the textColor , rangeColor and valueColor properties.

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" valueColor="PeachPuff" rangeColor="MediumTurquoise" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Reactive

Knob can be controlled with custom controls as well.

```vue
<template>
    <div class="flex flex-col items-center gap-2">
        <Knob v-model="value" :size="150" readonly />
        <div class="flex gap-2">
            <Button :disabled="value >= 100" iconOnly @click="value++">
                <Plus />
            </Button>
            <Button :disabled="value <= 0" iconOnly @click="value--">
                <Minus />
            </Button>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';

const value = ref(0);
<\/script>
```

## ReadOnly

When readonly present, value cannot be edited.

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" readonly />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Disabled

When disabled is present, a visual hint is applied to indicate that the Knob cannot be interacted with.

```vue
<template>
    <div class="flex justify-center">
        <Knob v-model="value" disabled />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(75);
<\/script>
```

## Forms

Knob integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4">
            <div class="flex flex-col items-center gap-1">
                <Knob name="knob" />
                <Message v-if="$form.knob?.invalid" severity="error" size="small" variant="simple">{{ $form.knob.error?.message }}</Message>
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
    knob: 15
});

const resolver = ref(zodResolver(
    z.object({
        knob: z.number().gt(25, { message: 'Must be greater than 25.' }).lt(75, { message: 'Must be less than 75.' })
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

Screen Reader Knob element component uses slider role in addition to the aria-valuemin , aria-valuemax and aria-valuenow attributes. Value to describe the component can be defined using ariaLabelledby and ariaLabel props. Keyboard Support Key Function tab Moves focus to the slider. left arrow down arrow Decrements the value. right arrow up arrow Increments the value. home Set the minimum value. end Set the maximum value. page up Increments the value by 10 steps. page down Decrements the value by 10 steps.

```vue
<template>
    <span id="label_number">Number</span>
    <Knob ariaLabelledby="label_number" />

    <Knob ariaLabel="Number" />
</template>
```

## Knob API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | number | - | Value of the component. |
| defaultValue | any | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | The name attribute for the element, typically used in form submissions. |
| size | number | 100 | Size of the component in pixels. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| readonly | boolean | false | When present, it specifies that the component value cannot be edited. |
| step | number | 1 | Step factor to increment/decrement the value. |
| min | number | 0 | Mininum boundary value. |
| max | number | 100 | Maximum boundary value. |
| valueColor | string | $dt('knob.value.background') | Background of the value. |
| rangeColor | string | $dt('knob.range.background') | Background color of the range. |
| textColor | string | $dt('knob.text.color') | Color of the value text. |
| strokeWidth | number | 14 | Width of the knob stroke. |
| showValue | boolean | true | Whether the show the value inside the knob. |
| valueTemplate | string \| Function | '{value}' | Template string of the value. |
| tabindex | number | 0 | Index of the element in tabbing order. |
| ariaLabelledby | string | - | Establishes relationships between the component and label(s) where its value should be one or more element IDs. |
| ariaLabel | string | - | Used to define a string that labels the element. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | KnobPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| svg | KnobPassThroughOptionType | Used to pass attributes to the svg's DOM element. |
| range | KnobPassThroughOptionType | Used to pass attributes to the range's DOM element. |
| value | KnobPassThroughOptionType | Used to pass attributes to the value' DOM element. |
| text | KnobPassThroughOptionType | Used to pass attributes to the text's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-knob | Class name of the root element |
| p-knob-range | Class name of the range element |
| p-knob-value | Class name of the value element |
| p-knob-text | Class name of the text element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| knob.transition.duration | --p-knob-transition-duration | Transition duration of root |
| knob.focus.ring.width | --p-knob-focus-ring-width | Focus ring width of root |
| knob.focus.ring.style | --p-knob-focus-ring-style | Focus ring style of root |
| knob.focus.ring.color | --p-knob-focus-ring-color | Focus ring color of root |
| knob.focus.ring.offset | --p-knob-focus-ring-offset | Focus ring offset of root |
| knob.focus.ring.shadow | --p-knob-focus-ring-shadow | Focus ring shadow of root |
| knob.value.background | --p-knob-value-background | Background of value |
| knob.range.background | --p-knob-range-background | Background of range |
| knob.text.color | --p-knob-text-color | Color of text |
| knob.text.font.size | --p-knob-text-font-size | Font size of text |
| knob.text.font.weight | --p-knob-text-font-weight | Font weight of text |
