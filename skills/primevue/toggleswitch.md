# ToggleSwitch

ToggleSwitch is used to select a boolean value.

## Basic

Toggles a boolean setting between enabled and disabled states.

```vue
<template>
    <div class="flex justify-center items-center gap-2">
        <label for="switch">Off</label>
        <ToggleSwitch v-model="checked" inputId="switch" />
        <label for="switch">On</label>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(false);
<\/script>
```

## Controlled

A controlled ToggleSwitch manages the checked state with v-model for two-way value binding.

```vue
<template>
    <div class="flex justify-center items-center gap-2">
        <ToggleSwitch v-model="checked" inputId="mode" />
        <label for="mode">Airplane Mode</label>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(true);
<\/script>
```

## Template

The handle slot is available to display custom content.

```vue
<template>
    <div class="flex justify-center">
        <ToggleSwitch v-model="checked">
            <template #handle="{ checked }">
                <Check v-if="checked" class="text-xs!" />
                <Times v-else class="text-xs!" />
            </template>
        </ToggleSwitch>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Check from '@primeicons/vue/check';
import Times from '@primeicons/vue/times';

const checked = ref(false);
<\/script>
```

## Customization

ToggleSwitch supports customization through the pt property. The appearance, including colors and other visual properties, can be modified by applying custom classes.

```vue
<template>
    <div>
        <label for="custom" class="max-w-xs mx-auto flex items-start gap-2 bg-slate-50 hover:bg-slate-100 dark:bg-slate-800 hover:dark:bg-slate-700 p-4 rounded-md transition-colors">
            <div class="flex flex-col gap-1 flex-1">
                <span class="m-0 text-medium text-slate-900 dark:text-slate-50">Try Beta Features</span>
                <span class="m-0 text-sm text-slate-400">Experience upcoming features before they're officially released.</span>
            </div>
            <ToggleSwitch
                v-model="checked"
                inputId="custom"
                :pt="{
                    slider: { class: checked ? 'bg-blue-300! rounded-md!' : 'bg-slate-300! dark:bg-slate-600! rounded-md!' },
                    handle: { class: checked ? 'bg-blue-900!' : 'bg-slate-500!' }
                }"
            />
        </label>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(true);
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused.

```vue
<template>
    <div class="flex justify-center">
        <ToggleSwitch v-model="checked" disabled />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(false);
<\/script>
```

## Invalid

The invalid state is applied using the invalid property to indicate failed validation, which can be integrated with form validation.

```vue
<template>
    <div class="flex justify-center">
        <ToggleSwitch v-model="checked" :invalid="!checked" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const checked = ref(false);
<\/script>
```

## Forms

ToggleSwitch integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4 w-48">
            <div class="flex flex-col items-center gap-2">
                <ToggleSwitch name="activation" />
                <Message v-if="$form.activation?.invalid" severity="error" size="small" variant="simple">{{ $form.activation.error?.message }}</Message>
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
    activation: false
});
const resolver = ref(zodResolver(
    z.object({
        activation: z.boolean().refine((val) => val === true, { message: 'Activation is required.' })
    })
));
<\/script>
```

## Accessibility

Screen Reader ToggleSwitch component uses a hidden native checkbox element with switch role internally that is only visible to screen readers. Value to describe the component can either be provided via label tag combined with inputId prop or using aria-labelledby , aria-label props. Keyboard Support Key Function tab Moves focus to the switch. space Toggles the checked state.

```vue
<template>
    <label for="switch1">Remember Me</label>
    <ToggleSwitch inputId="switch1" />

    <span id="switch2">Remember Me</span>
    <ToggleSwitch aria-labelledby="switch2" />

    <ToggleSwitch aria-label="Remember Me" />
</template>
```

## Toggle Switch API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | string \| boolean | false | Specifies whether a toggleswitch should be checked or not. |
| defaultValue | string \| boolean | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | The name attribute for the element, typically used in form submissions. |
| trueValue | any | true | Value in checked state. |
| falseValue | any | false | Value in unchecked state. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| readonly | boolean | - | When present, it specifies that an input field is read-only. |
| tabindex | number | - | Index of the element in tabbing order. |
| inputId | string | - | Identifier of the underlying input element. |
| inputClass | string \| object | - | Style class of the input field. |
| inputStyle | object | - | Inline style of the input field. |
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
| root | ToggleSwitchPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| input | ToggleSwitchPassThroughOptionType | Used to pass attributes to the input's DOM element. |
| slider | ToggleSwitchPassThroughOptionType | Used to pass attributes to the slider's DOM element. |
| handle | ToggleSwitchPassThroughOptionType | Used to pass attributes to the handle's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-toggleswitch | Class name of the root element |
| p-toggleswitch-input | Class name of the input element |
| p-toggleswitch-slider | Class name of the slider element |
| p-toggleswitch-handle | Class name of the handle element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| toggleswitch.width | --p-toggleswitch-width | Width of root |
| toggleswitch.height | --p-toggleswitch-height | Height of root |
| toggleswitch.border.radius | --p-toggleswitch-border-radius | Border radius of root |
| toggleswitch.gap | --p-toggleswitch-gap | Gap of root |
| toggleswitch.shadow | --p-toggleswitch-shadow | Shadow of root |
| toggleswitch.focus.ring.width | --p-toggleswitch-focus-ring-width | Focus ring width of root |
| toggleswitch.focus.ring.style | --p-toggleswitch-focus-ring-style | Focus ring style of root |
| toggleswitch.focus.ring.color | --p-toggleswitch-focus-ring-color | Focus ring color of root |
| toggleswitch.focus.ring.offset | --p-toggleswitch-focus-ring-offset | Focus ring offset of root |
| toggleswitch.focus.ring.shadow | --p-toggleswitch-focus-ring-shadow | Focus ring shadow of root |
| toggleswitch.border.width | --p-toggleswitch-border-width | Border width of root |
| toggleswitch.border.color | --p-toggleswitch-border-color | Border color of root |
| toggleswitch.hover.border.color | --p-toggleswitch-hover-border-color | Hover border color of root |
| toggleswitch.checked.border.color | --p-toggleswitch-checked-border-color | Checked border color of root |
| toggleswitch.checked.hover.border.color | --p-toggleswitch-checked-hover-border-color | Checked hover border color of root |
| toggleswitch.invalid.border.color | --p-toggleswitch-invalid-border-color | Invalid border color of root |
| toggleswitch.transition.duration | --p-toggleswitch-transition-duration | Transition duration of root |
| toggleswitch.slide.duration | --p-toggleswitch-slide-duration | Slide duration of root |
| toggleswitch.background | --p-toggleswitch-background | Background of root |
| toggleswitch.disabled.background | --p-toggleswitch-disabled-background | Disabled background of root |
| toggleswitch.hover.background | --p-toggleswitch-hover-background | Hover background of root |
| toggleswitch.checked.background | --p-toggleswitch-checked-background | Checked background of root |
| toggleswitch.checked.hover.background | --p-toggleswitch-checked-hover-background | Checked hover background of root |
| toggleswitch.handle.border.radius | --p-toggleswitch-handle-border-radius | Border radius of handle |
| toggleswitch.handle.size | --p-toggleswitch-handle-size | Size of handle |
| toggleswitch.handle.background | --p-toggleswitch-handle-background | Background of handle |
| toggleswitch.handle.disabled.background | --p-toggleswitch-handle-disabled-background | Disabled background of handle |
| toggleswitch.handle.hover.background | --p-toggleswitch-handle-hover-background | Hover background of handle |
| toggleswitch.handle.checked.background | --p-toggleswitch-handle-checked-background | Checked background of handle |
| toggleswitch.handle.checked.hover.background | --p-toggleswitch-handle-checked-hover-background | Checked hover background of handle |
| toggleswitch.handle.color | --p-toggleswitch-handle-color | Color of handle |
| toggleswitch.handle.hover.color | --p-toggleswitch-handle-hover-color | Hover color of handle |
| toggleswitch.handle.checked.color | --p-toggleswitch-handle-checked-color | Checked color of handle |
| toggleswitch.handle.checked.hover.color | --p-toggleswitch-handle-checked-hover-color | Checked hover color of handle |
