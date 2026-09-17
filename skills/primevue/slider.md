# Slider

Slider is a component to provide input by dragging a handle along a track.

## Basic

Select a numeric value by dragging a handle along a track. Two-way binding is defined using the standard v-model directive.

```vue
<template>
    <Slider v-model="value" class="max-w-3xs mx-auto w-full" />
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Step

Size of each movement is defined with the step property.

```vue
<template>
    <Slider v-model="value" :step="20" class="max-w-3xs mx-auto w-full" />
</template>

<script setup>
import { ref } from 'vue';

const value = ref(20);
<\/script>
```

## Range

When the range property is present, slider provides two handles to define two values. In range mode, the value should be an array instead of a single value.

```vue
<template>
    <Slider v-model="rangeValues" range class="max-w-3xs mx-auto w-full" />
</template>

<script setup>
import { ref } from 'vue';

const rangeValues = ref([20, 80]);
<\/script>
```

## Handles Distance

The minStepsBetweenHandles property defines the minimum number of steps between handles in range mode.

```vue
<template>
    <Slider v-model="rangeValues" range :minStepsBetweenHandles="20" class="max-w-3xs mx-auto w-full" />
</template>

<script setup>
import { ref } from 'vue';

const rangeValues = ref([20, 80]);
<\/script>
```

## Vertical

Default layout of slider is horizontal , use orientation property for the alternative vertical mode.

```vue
<template>
    <div class="grid grid-cols-3 h-56 gap-4 w-fit mx-auto">
        <div v-for="slider in sliders" :key="slider.label" class="flex flex-col items-center justify-center gap-3">
            <Slider v-model="slider.value" orientation="vertical" />
            <span class="font-mono text-xs uppercase text-surface-500">{{ slider.label }}</span>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const sliders = ref([
    { label: 'Bass', value: 40 },
    { label: 'Mid', value: 70 },
    { label: 'Treble', value: 55 }
]);
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused.

```vue
<template>
    <div class="max-w-3xs w-full mx-auto space-y-12">
        <div>
            <h5 class="mb-2 text-sm font-medium">Disabled Slider</h5>
            <Slider v-model="value" disabled />
        </div>
        <div>
            <h5 class="mb-2 text-sm font-medium">Disabled All Handles</h5>
            <Slider v-model="rangeValues" range disabled />
        </div>
        <div>
            <h5 class="mb-2 text-sm font-medium">Disabled Single Handle</h5>
            <Slider v-model="rangeValues2" range disabledMinHandle />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
const rangeValues = ref([20, 80]);
const rangeValues2 = ref([20, 80]);
<\/script>
```

## Controlled

Slider is connected to an InputNumber using two-way binding.

```vue
<template>
    <div class="max-w-3xs w-full mx-auto">
        <InputNumber v-model="value" :showButtons="false" fluid class="mb-4" />
        <Slider v-model="value" class="w-full" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Value Change

The change event is triggered during drag, while slideend is fired when the drag operation completes.

```vue
<template>
    <div class="max-w-3xs mx-auto w-full flex flex-col items-center space-y-4">
        <div class="text-sm text-surface-500 font-mono">change: {{ value }}</div>
        <div class="text-sm text-surface-500 font-mono">slideend: {{ endValue }}</div>
        <Slider v-model="value" @change="onChange" @slideend="onSlideEnd" class="w-full" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
const endValue = ref(50);

const onChange = (event) => {
    value.value = event;
};

const onSlideEnd = (event) => {
    endValue.value = event.value;
};
<\/script>
```

## Custom

Slider is customized with the pt property to override the style of each section.

```vue
<template>
    <div>
        <div class="max-w-xs mx-auto w-full space-y-16">
        <Slider
                v-model="value1"
                :pt="{
                track: { class: 'h-2! bg-blue-100! dark:bg-blue-950!' },
                range: { class: 'bg-blue-500!' },
                handle: { class: 'before:hidden! border-2! border-blue-500! bg-surface-0! dark:bg-surface-900! rotate-45! rounded-md!' }
            }"
        />

        <Slider
                v-model="value2"
                :pt="{
                track: { class: 'h-2! bg-amber-100! dark:bg-amber-950!' },
                range: { class: 'bg-amber-500!' },
                handle: { class: 'before:hidden! w-4! h-5! border-2! border-amber-500! bg-surface-0! dark:bg-surface-900! rounded-sm!' }
            }"
        />

        <div class="relative">
            <VolumeUp class="text-surface-400 absolute left-2 top-1/2 -translate-y-1/2 z-10" />
            <Slider
                    v-model="value3"
                    class="h-8! rounded-full!"
                :pt="{
                    track: { class: 'h-full! rounded-full! border border-surface-100 dark:border-surface-900 bg-surface-100! dark:bg-surface-900!' },
                    range: { class: 'rounded-full! bg-surface-0!', style: { width: \`clamp(2rem, calc(\${value3}% + 1rem), 100%)\` } },
                    handle: {
                        class: 'z-20 h-[calc(100%+2px)]! dark:h-full! aspect-square! w-auto! before:hidden! bg-surface-0! border! border-surface-200! shadow-sm',
                        style: { insetInlineStart: \`clamp(1rem, \${value3}%, calc(100% - 1rem))\` }
                    }
                }"
            />
        </div>

        <div class="relative">
            <div class="h-8! flex! items-center gap-1 w-full bg-transparent! cursor-grab active:cursor-grabbing relative">
                <span class="absolute left-0 top-0 bg-linear-to-r from-sky-200 via-indigo-200 to-blue-400 h-full rounded-full" :style="{ width: \`clamp(0px, calc(\${value4}% - 1.25rem), calc(100% - 2.25rem))\` }"></span>
                <span
                        class="absolute top-0 h-full bg-surface-100 dark:bg-surface-900 rounded-full"
                        :style="{
                        left: \`clamp(2.25rem, calc(\${value4}% + 1.25rem), 100%)\`,
                        width: \`calc(100% - clamp(2.25rem, calc(\${value4}% + 1.25rem), 100%))\`
                    }"
                ></span>
            </div>
            <Slider
                    v-model="value4"
                    class="absolute! inset-0 h-8!"
                :pt="{
                    track: { class: 'h-8! flex! items-center gap-1 w-full bg-transparent! cursor-grab active:cursor-grabbing' },
                    range: { class: 'hidden!' },
                    handle: {
                        class: 'before:hidden! size-8! shrink-0 bg-surface-0! dark:bg-surface-800! border border-surface-200! dark:border-surface-700! shadow-sm',
                        style: { insetInlineStart: \`clamp(1rem, \${value4}%, calc(100% - 1rem))\` }
                    }
                }"
            />
        </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(50);
const value2 = ref(50);
const value3 = ref(50);
const value4 = ref(50);
<\/script>
```

## Filter

Image filter implementation using multiple sliders.

```vue
<template>
    <div class="flex flex-col items-center justify-center">
        <img alt="user header" class="w-80 rounded mb-6" src="https://primefaces.org/cdn/primevue/images/galleria/galleria1.jpg" :style="filterStyle" />
        <SelectButton v-model="filter" :options="filterOptions" optionLabel="label" optionValue="value" />
        <Slider v-model="filterValues[filter]" class="max-w-56 mt-4" :min="0" :max="200" />
    </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const filter = ref(0);
const filterValues = ref([100, 100, 0]);
const filterOptions = ref([
    { label: 'Contrast', value: 0 },
    { label: 'Brightness', value: 1 },
    { label: 'Sepia', value: 2 }
]);
const filterStyle = computed(() => {
    return {
        filter: \`contrast(\${filterValues.value[0]}%) brightness(\${filterValues.value[1]}%) sepia(\${filterValues.value[2]}%)\`
    };
});
<\/script>
```

## Forms

Slider integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4 w-full sm:w-56">
            <div class="flex flex-col gap-4">
                <Slider name="value" />
                <Message v-if="$form.value?.invalid" severity="error" size="small" variant="simple">{{ $form.value.error?.message }}</Message>
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
    value: 0
});
const resolver = ref(zodResolver(
    z.object({
        value: z.number().gt(25, { message: 'Must be greater than 25.' })
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

Screen Reader Slider element component uses slider role on the handle in addition to the aria-orientation , aria-valuemin , aria-valuemax and aria-valuenow attributes. Value to describe the component can be defined using aria-labelledby and aria-label props. Keyboard Support Key Function tab Moves focus to the slider. left arrow up arrow Decrements the value. right arrow down arrow Increments the value. home Set the minimum value. end Set the maximum value. page up Increments the value by 10 steps. page down Decrements the value by 10 steps.

```vue
<template>
    <span id="label_number">Number</span>
    <Slider aria-labelledby="label_number" />

    <Slider aria-label="Number" />
</template>
```

## Slider API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | number \| number[] | - | Value of the component. |
| defaultValue | number \| number[] | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | The name attribute for the element, typically used in form submissions. |
| min | number | 0 | Mininum boundary value. |
| max | number | 100 | Maximum boundary value. |
| orientation | any | horizontal | Orientation of the slider. |
| step | number | 1 | Step factor to increment/decrement the value. |
| range | boolean | false | When speficed, allows two boundary values to be picked. |
| readonly | boolean | false | When present, the component cannot be edited while it is still focusable and visually unchanged. |
| disabledMinHandle | boolean | false | When present and  `range`  is enabled, disables only the minimum (start) handle while keeping the maximum handle interactive. |
| disabledMaxHandle | boolean | false | When present and  `range`  is enabled, disables only the maximum (end) handle while keeping the minimum handle interactive. |
| minStepsBetweenHandles | number | 0 | The minimum permitted steps between multiple handles in range mode. |
| inputId | string | - | Identifier of the underlying hidden input element. In range mode, applied to the first handle's input. |
| inputClass | string \| object | - | Style class of the hidden input element. |
| inputStyle | object | - | Inline style of the hidden input element. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| tabindex | number | - | Index of the element in tabbing order. |
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
| root | SliderPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| range | SliderPassThroughOptionType | Used to pass attributes to the range's DOM element. |
| handle | SliderPassThroughOptionType | Used to pass attributes to the handle's DOM element. |
| startHandler | SliderPassThroughOptionType | Used to pass attributes to the start handler's DOM element. |
| endHandler | SliderPassThroughOptionType | Used to pass attributes to the end handler's DOM element. |
| input | SliderPassThroughOptionType | Used to pass attributes to the hidden input's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-slider | Class name of the root element |
| p-slider-range | Class name of the range element |
| p-slider-handle | Class name of the handle element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| slider.transition.duration | --p-slider-transition-duration | Transition duration of root |
| slider.track.background | --p-slider-track-background | Background of track |
| slider.track.border.radius | --p-slider-track-border-radius | Border radius of track |
| slider.track.size | --p-slider-track-size | Size of track |
| slider.range.background | --p-slider-range-background | Background of range |
| slider.handle.width | --p-slider-handle-width | Width of handle |
| slider.handle.height | --p-slider-handle-height | Height of handle |
| slider.handle.border.radius | --p-slider-handle-border-radius | Border radius of handle |
| slider.handle.background | --p-slider-handle-background | Background of handle |
| slider.handle.hover.background | --p-slider-handle-hover-background | Hover background of handle |
| slider.handle.content.border.radius | --p-slider-handle-content-border-radius | Content border radius of handle |
| slider.handle.content.background | --p-slider-handle-content-background | Background of handle |
| slider.handle.content.hover.background | --p-slider-handle-content-hover-background | Content hover background of handle |
| slider.handle.content.width | --p-slider-handle-content-width | Content width of handle |
| slider.handle.content.height | --p-slider-handle-content-height | Content height of handle |
| slider.handle.content.shadow | --p-slider-handle-content-shadow | Content shadow of handle |
| slider.handle.focus.ring.width | --p-slider-handle-focus-ring-width | Focus ring width of handle |
| slider.handle.focus.ring.style | --p-slider-handle-focus-ring-style | Focus ring style of handle |
| slider.handle.focus.ring.color | --p-slider-handle-focus-ring-color | Focus ring color of handle |
| slider.handle.focus.ring.offset | --p-slider-handle-focus-ring-offset | Focus ring offset of handle |
| slider.handle.focus.ring.shadow | --p-slider-handle-focus-ring-shadow | Focus ring shadow of handle |
