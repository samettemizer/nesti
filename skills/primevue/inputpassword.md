# InputPassword

InputPassword is an enhanced input for password entry with strength metering, mask toggling, and controlled or uncontrolled usage.

## Basic

InputPassword is used as a controlled input with v-model property.

```vue
<template>
    <div class="flex justify-center">
        <InputPassword v-model="value" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Toggle Mask

Adding a toggle icon to show or hide the password, allowing users to verify their input.

```vue
<template>
    <div class="flex justify-center">
        <IconField>
            <InputPassword v-model="value" :mask="mask" />
            <InputIcon class="cursor-pointer" @click="mask = !mask">
                <Eye v-if="mask" />
                <EyeSlash v-else />
            </InputIcon>
        </IconField>
    </div>
</template>

<script setup>
import Eye from '@primeicons/vue/eye';
import EyeSlash from '@primeicons/vue/eye-slash';
import { ref } from 'vue';

const value = ref('');
const mask = ref(true);
<\/script>
```

## Requirements

Password requirements checklist with real-time validation feedback.

```vue
<template>
    <div class="flex justify-center">
        <div class="flex flex-col gap-2 w-64">
            <InputPassword v-model="value" placeholder="Enter password" />
            <ul class="flex flex-col gap-2 list-none ms-1 my-1 p-0">
                <li v-for="req in requirements" :key="req.id" class="flex items-center gap-2 text-sm transition-all duration-300">
                    <CheckCircle :class="['transition-all duration-300 ease-out', req.test(value) ? 'text-green-500 scale-110 opacity-100' : 'text-surface-400 scale-90 opacity-70']" />
                    <span :class="['transition-all duration-300 ease-out', req.test(value) ? 'text-green-700 dark:text-green-400 line-through decoration-2 decoration-green-500/70' : 'text-surface-700 dark:text-surface-300 dark:opacity-70']">
                        {{ req.label }}
                    </span>
                </li>
            </ul>
        </div>
    </div>
</template>

<script setup>
import CheckCircle from '@primeicons/vue/check-circle';
import { ref } from 'vue';

const value = ref('');
const requirements = [
    { id: 'minLength', label: 'At least 12 characters', test: (v) => v.length >= 12 },
    { id: 'uppercase', label: 'Contains uppercase letter', test: (v) => /[A-Z]/.test(v) },
    { id: 'lowercase', label: 'Contains lowercase letter', test: (v) => /[a-z]/.test(v) },
    { id: 'number', label: 'Contains number', test: (v) => /[0-9]/.test(v) },
    { id: 'symbol', label: 'Contains special character', test: (v) => /[^a-zA-Z0-9]/.test(v) }
];
<\/script>
```

## Strength Meter

Visualize the overall password strength with an animated progress bar and a severity-based label that adapts as the password improves.

```vue
<template>
    <div class="flex justify-center">
        <div class="flex flex-col gap-2 w-64">
            <InputPassword v-model="value" placeholder="Enter password" />
            <div class="flex flex-col gap-2" :style="{ visibility: info ? 'visible' : 'hidden' }">
                <ProgressBar :value="info?.percent ?? 0" :show-value="false" :pt="{ value: { style: { backgroundColor: info?.color } } }" style="height: 6px" />
                <div class="flex justify-end">
                    <Tag :severity="info?.severity ?? 'info'" :value="info?.label ?? '—'" />
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const strengthMap = {
    weak: { label: 'Weak', percent: 25, color: 'var(--p-red-400)', severity: 'danger' },
    medium: { label: 'Medium', percent: 50, color: 'var(--p-amber-400)', severity: 'warn' },
    strong: { label: 'Strong', percent: 75, color: 'var(--p-blue-400)', severity: 'info' },
    'very-strong': { label: 'Very Strong', percent: 100, color: 'var(--p-emerald-400)', severity: 'success' }
};

function getStrength(value) {
    if (!value) return null;

    let score = 0;

    if (value.length >= 8) score++;
    if (value.length >= 12) score++;
    if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score++;
    if (/[0-9]/.test(value)) score++;
    if (/[^a-zA-Z0-9]/.test(value)) score++;

    if (score <= 1) return 'weak';
    else if (score <= 2) return 'medium';
    else if (score <= 3) return 'strong';

    return 'very-strong';
}

const value = ref('');
const info = computed(() => {
    const level = getStrength(value.value);

    return level ? strengthMap[level] : null;
});
<\/script>
```

## Popover

Combine a visibility toggle, strength meter, and requirements checklist into a fully custom password creation with Popover component.

```vue
<template>
    <div class="flex justify-center">
        <div class="flex flex-col gap-2">
            <IconField>
                <InputPassword v-model="value" :mask="mask" placeholder="Create a password" @focus="onFocus" @blur="onBlur" />
                <InputIcon class="cursor-pointer" @click="mask = !mask">
                    <Eye v-if="mask" />
                    <EyeSlash v-else />
                </InputIcon>
            </IconField>
            <Popover ref="op">
                <div class="flex flex-col gap-3 w-72">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <Shield style="width: 1.25rem; height: 1.25rem" />
                            <span class="font-semibold text-sm">Password Strength</span>
                        </div>
                        <Tag :severity="severity" :value="label || '—'" :style="{ visibility: label ? 'visible' : 'hidden' }" />
                    </div>
                    <ProgressBar :value="score" :show-value="false" :pt="{ value: { style: { backgroundColor: color } } }" style="height: 6px" />
                    <ul class="flex flex-col gap-2 list-none m-0 p-0">
                        <li v-for="rule in rules" :key="rule.id" class="flex items-center gap-2 text-xs">
                            <Check v-if="rule.test(value)" class="text-green-500" />
                            <Times v-else class="text-red-400" />
                            <span :class="rule.test(value) ? 'text-surface-500' : 'text-surface-700'">{{ rule.label }}</span>
                        </li>
                    </ul>
                </div>
            </Popover>
        </div>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import Eye from '@primeicons/vue/eye';
import EyeSlash from '@primeicons/vue/eye-slash';
import Shield from '@primeicons/vue/shield';
import Times from '@primeicons/vue/times';
import { computed, ref } from 'vue';

const rules = [
    { id: 'length', label: 'At least 12 characters long', test: (v) => v.length >= 12, weight: 20 },
    { id: 'uppercase', label: 'Contains uppercase letter', test: (v) => /[A-Z]/.test(v), weight: 20 },
    { id: 'lowercase', label: 'Contains lowercase letter', test: (v) => /[a-z]/.test(v), weight: 20 },
    { id: 'number', label: 'Contains number', test: (v) => /[0-9]/.test(v), weight: 20 },
    { id: 'special', label: 'Contains special character (!@#$...)', test: (v) => /[^a-zA-Z0-9]/.test(v), weight: 20 }
];

const value = ref('');
const mask = ref(true);
const op = ref();

const score = computed(() => {
    if (!value.value) return 0;

    return rules.reduce((acc, rule) => acc + (rule.test(value.value) ? rule.weight : 0), 0);
});

const severity = computed(() => {
    if (score.value <= 20) return 'danger';
    if (score.value <= 40) return 'warn';
    if (score.value <= 60) return 'info';

    return 'success';
});

const color = computed(() => {
    switch (severity.value) {
        case 'danger':
            return 'var(--p-red-500)';
        case 'warn':
            return 'var(--p-amber-500)';
        case 'info':
            return 'var(--p-blue-500)';
        default:
            return 'var(--p-green-500)';
    }
});

const label = computed(() => {
    if (score.value === 0) return '';
    if (score.value <= 20) return 'Too Weak';
    if (score.value <= 40) return 'Weak';
    if (score.value <= 60) return 'Fair';
    if (score.value <= 80) return 'Strong';

    return 'Very Strong';
});

const onFocus = (event) => op.value.show(event);
const onBlur = () => op.value.hide();
<\/script>
```

## Float Label

FloatLabel visually integrates a label with its form element. Visit FloatLabel documentation for more information.

```vue
<template>
    <div class="flex flex-wrap justify-center items-end gap-4">
        <FloatLabel>
            <InputPassword id="over_label" v-model="value1" autocomplete="off" />
            <label for="over_label">Password</label>
        </FloatLabel>

        <FloatLabel variant="in">
            <InputPassword id="in_label" v-model="value2" autocomplete="off" />
            <label for="in_label">Password</label>
        </FloatLabel>

        <FloatLabel variant="on">
            <InputPassword id="on_label" v-model="value3" autocomplete="off" />
            <label for="on_label">Password</label>
        </FloatLabel>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(null);
const value2 = ref(null);
const value3 = ref(null);
<\/script>
```

## Ifta Label

IftaLabel is used to create infield top aligned labels. Visit IftaLabel documentation for more information.

```vue
<template>
    <div class="flex justify-center">
        <IftaLabel>
            <InputPassword id="password" v-model="value" variant="filled" autocomplete="off" />
            <label for="password">Password</label>
        </IftaLabel>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(null);
<\/script>
```

## Clear Icon

Use a custom clear action to reset the password input.

```vue
<template>
    <div class="flex justify-center">
        <IconField>
            <InputPassword v-model="value" class="w-56" />
            <InputIcon v-if="value" class="cursor-pointer" @click="value = ''">
                <Times />
            </InputIcon>
        </IconField>
    </div>
</template>

<script setup>
import Times from '@primeicons/vue/times';
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Fluid

Fluid spans the full width of the container.

```vue
<template>
    <div>
        <InputPassword v-model="value" fluid />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Sizes

InputPassword provides small and large sizes as alternatives to the base.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <InputPassword v-model="value1" size="small" placeholder="Small" />
        <InputPassword v-model="value2" placeholder="Normal" />
        <InputPassword v-model="value3" size="large" placeholder="Large" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref('');
const value2 = ref('');
const value3 = ref('');
<\/script>
```

## Filled

Specify the variant property as filled to display the component with a higher visual emphasis than the default outlined style.

```vue
<template>
    <div class="flex justify-center">
        <InputPassword v-model="value" variant="filled" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused.

```vue
<template>
    <div class="flex justify-center">
        <InputPassword disabled placeholder="Disabled" />
    </div>
</template>
```

## Invalid

The invalid state is applied using the invalid property to indicate failed validation, which can be integrated with form validation.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-4">
        <InputPassword v-model="value1" :invalid="!value1" placeholder="Password" />
        <InputPassword v-model="value2" :invalid="!value2" variant="filled" placeholder="Password" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref('');
const value2 = ref('');
<\/script>
```

## Forms

InputPassword integrates seamlessly with the PrimeVue Forms library. This example validates password strength and confirms the value matches.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4 w-full sm:w-72">
            <div class="flex flex-col gap-1">
                <InputPassword name="password" placeholder="New password" autocomplete="off" fluid />
                <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">{{ $form.password.error?.message }}</Message>
            </div>
            <div class="flex flex-col gap-1">
                <InputPassword name="confirmPassword" placeholder="Confirm password" autocomplete="off" fluid />
                <Message v-if="$form.confirmPassword?.invalid" severity="error" size="small" variant="simple">{{ $form.confirmPassword.error?.message }}</Message>
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
    password: '',
    confirmPassword: ''
});

const resolver = ref(zodResolver(
    z
        .object({
            password: z
                .string()
                .min(1, { message: 'Password is required.' })
                .min(8, { message: 'Password must be at least 8 characters.' })
                .regex(/[a-z]/, { message: 'Must contain a lowercase letter.' })
                .regex(/[A-Z]/, { message: 'Must contain an uppercase letter.' })
                .regex(/[0-9]/, { message: 'Must contain a number.' })
                .regex(/[^a-zA-Z0-9]/, { message: 'Must contain a special character.' }),
            confirmPassword: z.string().min(1, { message: 'Please confirm your password.' })
        })
        .refine((data) => data.password === data.confirmPassword, {
            message: 'Passwords do not match.',
            path: ['confirmPassword']
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

Screen Reader InputPassword is applied to a native input element so it implicitly includes any passed prop. Value to describe the component can either be provided via label tag combined with id prop or using aria-labelledby , aria-label props. Keyboard Support Key Function tab Moves focus to the input.

```vue
<template>
    <label for="pwd1">Password</label>
    <InputPassword id="pwd1" />

    <span id="pwd2">Password</span>
    <InputPassword aria-labelledby="pwd2" />

    <InputPassword aria-label="Password" />
</template>
```

## Input Password API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| aria-activedescendant | string | - | Identifies the currently active element when DOM focus is on a composite widget, textbox, group, or application. |
| aria-atomic | Booleanish | - | Indicates whether assistive technologies will present all, or only parts of, the changed region based on the change notifications defined by the aria-relevant attribute. |
| aria-autocomplete | "none" \| "inline" \| "list" \| "both" | - | Indicates whether inputting text could trigger display of one or more predictions of the user's intended value for an input and specifies how predictions would be presented if they are made. |
| aria-busy | Booleanish | - | Indicates an element is being modified and that assistive technologies MAY want to wait until the modifications are complete before exposing them to the user. |
| aria-checked | Booleanish \| "mixed" | - | Indicates the current "checked" state of checkboxes, radio buttons, and other widgets. |
| aria-colcount | Numberish | - | Defines the total number of columns in a table, grid, or treegrid. |
| aria-colindex | Numberish | - | Defines an element's column index or position with respect to the total number of columns within a table, grid, or treegrid. |
| aria-colspan | Numberish | - | Defines the number of columns spanned by a cell or gridcell within a table, grid, or treegrid. |
| aria-controls | string | - | Identifies the element (or elements) whose contents or presence are controlled by the current element. |
| aria-current | Booleanish \| "page" \| "step" \| "location" \| "date" \| "time" | - | Indicates the element that represents the current item within a container or set of related elements. |
| aria-describedby | string | - | Identifies the element (or elements) that describes the object. |
| aria-details | string | - | Identifies the element that provides a detailed, extended description for the object. |
| aria-disabled | Booleanish | - | Indicates that the element is perceivable but disabled, so it is not editable or otherwise operable. |
| aria-dropeffect | "link" \| "none" \| "copy" \| "execute" \| "move" \| "popup" | - | Indicates what functions can be performed when a dragged object is released on the drop target. |
| aria-errormessage | string | - | Identifies the element that provides an error message for the object. |
| aria-expanded | Booleanish | - | Indicates whether the element, or another grouping element it controls, is currently expanded or collapsed. |
| aria-flowto | string | - | Identifies the next element (or elements) in an alternate reading order of content which, at the user's discretion, allows assistive technology to override the general default of reading in document source order. |
| aria-grabbed | Booleanish | - | Indicates an element's "grabbed" state in a drag-and-drop operation. |
| aria-haspopup | Booleanish \| "menu" \| "listbox" \| "tree" \| "grid" \| "dialog" | - | Indicates the availability and type of interactive popup element, such as menu or dialog, that can be triggered by an element. |
| aria-hidden | Booleanish | - | Indicates whether the element is exposed to an accessibility API. |
| aria-invalid | Booleanish \| "grammar" \| "spelling" | - | Indicates the entered value does not conform to the format expected by the application. |
| aria-keyshortcuts | string | - | Indicates keyboard shortcuts that an author has implemented to activate or give focus to an element. |
| aria-label | string | - | Defines a string value that labels the current element. |
| aria-labelledby | string | - | Identifies the element (or elements) that labels the current element. |
| aria-level | Numberish | - | Defines the hierarchical level of an element within a structure. |
| aria-live | "off" \| "assertive" \| "polite" | - | Indicates that an element will be updated, and describes the types of updates the user agents, assistive technologies, and user can expect from the live region. |
| aria-modal | Booleanish | - | Indicates whether an element is modal when displayed. |
| aria-multiline | Booleanish | - | Indicates whether a text box accepts multiple lines of input or only a single line. |
| aria-multiselectable | Booleanish | - | Indicates that the user may select more than one item from the current selectable descendants. |
| aria-orientation | "horizontal" \| "vertical" | - | Indicates whether the element's orientation is horizontal, vertical, or unknown/ambiguous. |
| aria-owns | string | - | Identifies an element (or elements) in order to define a visual, functional, or contextual parent/child relationship between DOM elements where the DOM hierarchy cannot be used to represent the relationship. |
| aria-placeholder | string | - | Defines a short hint (a word or short phrase) intended to aid the user with data entry when the control has no value. A hint could be a sample value or a brief description of the expected format. |
| aria-posinset | Numberish | - | Defines an element's number or position in the current set of listitems or treeitems. Not required if all elements in the set are present in the DOM. |
| aria-pressed | Booleanish \| "mixed" | - | Indicates the current "pressed" state of toggle buttons. |
| aria-readonly | Booleanish | - | Indicates that the element is not editable, but is otherwise operable. |
| aria-relevant | "text" \| "additions" \| "additions removals" \| "additions text" \| "all" \| "removals" \| "removals additions" \| "removals text" \| "text additions" \| "text removals" | - | Indicates what notifications the user agent will trigger when the accessibility tree within a live region is modified. |
| aria-required | Booleanish | - | Indicates that user input is required on the element before a form may be submitted. |
| aria-roledescription | string | - | Defines a human-readable, author-localized description for the role of an element. |
| aria-rowcount | Numberish | - | Defines the total number of rows in a table, grid, or treegrid. |
| aria-rowindex | Numberish | - | Defines an element's row index or position with respect to the total number of rows within a table, grid, or treegrid. |
| aria-rowspan | Numberish | - | Defines the number of rows spanned by a cell or gridcell within a table, grid, or treegrid. |
| aria-selected | Booleanish | - | Indicates the current "selected" state of various widgets. |
| aria-setsize | Numberish | - | Defines the number of items in the current set of listitems or treeitems. Not required if all elements in the set are present in the DOM. |
| aria-sort | "none" \| "ascending" \| "descending" \| "other" | - | Indicates if items in a table or grid are sorted in ascending or descending order. |
| aria-valuemax | Numberish | - | Defines the maximum allowed value for a range widget. |
| aria-valuemin | Numberish | - | Defines the minimum allowed value for a range widget. |
| aria-valuenow | Numberish | - | Defines the current value for a range widget. |
| aria-valuetext | string | - | Defines the human readable text alternative of aria-valuenow for a range widget. |
| innerHTML | string | - |  |
| class | ClassValue | - |  |
| style | StyleValue | - |  |
| accesskey | string | - |  |
| contenteditable | Booleanish \| "inherit" \| "plaintext-only" | - |  |
| contextmenu | string | - |  |
| dir | string | - |  |
| draggable | Booleanish | - |  |
| enterkeyhint | "enter" \| "done" \| "go" \| "next" \| "previous" \| "search" \| "send" | - |  |
| enterKeyHint | "enter" \| "done" \| "go" \| "next" \| "previous" \| "search" \| "send" | - |  |
| hidden | "" \| Booleanish \| "hidden" \| "until-found" | - |  |
| id | string | - |  |
| inert | Booleanish | - |  |
| lang | string | - |  |
| spellcheck | Booleanish | - |  |
| tabindex | Numberish | - |  |
| title | string | - |  |
| translate | "yes" \| "no" | - |  |
| radiogroup | string | - |  |
| role | string | - |  |
| about | string | - |  |
| datatype | string | - |  |
| inlist | any | - |  |
| prefix | string | - |  |
| property | string | - |  |
| resource | string | - |  |
| typeof | string | - |  |
| vocab | string | - |  |
| autocapitalize | string | - |  |
| autocorrect | string | - |  |
| autosave | string | - |  |
| color | string | - |  |
| itemprop | string | - |  |
| itemscope | Booleanish | - |  |
| itemtype | string | - |  |
| itemid | string | - |  |
| itemref | string | - |  |
| results | Numberish | - |  |
| security | string | - |  |
| unselectable | "on" \| "off" | - |  |
| inputmode | "text" \| "search" \| "none" \| "tel" \| "url" \| "email" \| "numeric" \| "decimal" | - | Hints at the type of data that might be entered by the user while editing the element or its contents |
| is | string | - | Specify that a standard HTML element should behave like a defined custom built-in element |
| exportparts | string | - |  |
| part | string | - |  |
| accept | string | - |  |
| alt | string | - |  |
| autocomplete | InputAutoCompleteAttribute | - |  |
| autofocus | Booleanish | - |  |
| capture | boolean \| "user" \| "environment" | - |  |
| checked | any[] \| Set<any> \| Booleanish | - |  |
| crossorigin | string | - |  |
| form | string | - |  |
| formaction | string | - |  |
| formenctype | string | - |  |
| formmethod | string | - |  |
| formnovalidate | Booleanish | - |  |
| formtarget | string | - |  |
| height | Numberish | - |  |
| indeterminate | boolean | - |  |
| list | string | - |  |
| max | Numberish | - |  |
| maxlength | Numberish | - |  |
| min | Numberish | - |  |
| minlength | Numberish | - |  |
| multiple | Booleanish | - |  |
| pattern | string | - |  |
| placeholder | string | - |  |
| readonly | Booleanish | - |  |
| required | Booleanish | - |  |
| src | string | - |  |
| step | Numberish | - |  |
| type | InputTypeHTMLAttribute | - |  |
| value | any | - |  |
| width | Numberish | - |  |
| onCancel | Function | - |  |
| onCopy | Function | - |  |
| onCut | Function | - |  |
| onPaste | Function | - |  |
| onCompositionend | Function | - |  |
| onCompositionstart | Function | - |  |
| onCompositionupdate | Function | - |  |
| onDrag | Function | - |  |
| onDragend | Function | - |  |
| onDragenter | Function | - |  |
| onDragexit | Function | - |  |
| onDragleave | Function | - |  |
| onDragover | Function | - |  |
| onDragstart | Function | - |  |
| onDrop | Function | - |  |
| onFocus | Function | - |  |
| onFocusin | Function | - |  |
| onFocusout | Function | - |  |
| onBlur | Function | - |  |
| onChange | Function | - |  |
| onBeforeinput | Function | - |  |
| onFormdata | Function | - |  |
| onInput | Function | - |  |
| onReset | Function | - |  |
| onSubmit | Function | - |  |
| onInvalid | Function | - |  |
| onFullscreenchange | Function | - |  |
| onFullscreenerror | Function | - |  |
| onLoad | Function | - |  |
| onError | Function | - |  |
| onKeydown | Function | - |  |
| onKeypress | Function | - |  |
| onKeyup | Function | - |  |
| onDblclick | Function | - |  |
| onMousedown | Function | - |  |
| onMouseenter | Function | - |  |
| onMouseleave | Function | - |  |
| onMousemove | Function | - |  |
| onMouseout | Function | - |  |
| onMouseover | Function | - |  |
| onMouseup | Function | - |  |
| onAbort | Function | - |  |
| onCanplay | Function | - |  |
| onCanplaythrough | Function | - |  |
| onDurationchange | Function | - |  |
| onEmptied | Function | - |  |
| onEncrypted | Function | - |  |
| onEnded | Function | - |  |
| onLoadeddata | Function | - |  |
| onLoadedmetadata | Function | - |  |
| onLoadstart | Function | - |  |
| onPause | Function | - |  |
| onPlay | Function | - |  |
| onPlaying | Function | - |  |
| onProgress | Function | - |  |
| onRatechange | Function | - |  |
| onSeeked | Function | - |  |
| onSeeking | Function | - |  |
| onStalled | Function | - |  |
| onSuspend | Function | - |  |
| onTimeupdate | Function | - |  |
| onVolumechange | Function | - |  |
| onWaiting | Function | - |  |
| onSelect | Function | - |  |
| onScroll | Function | - |  |
| onScrollend | Function | - |  |
| onTouchcancel | Function | - |  |
| onTouchend | Function | - |  |
| onTouchmove | Function | - |  |
| onTouchstart | Function | - |  |
| onAuxclick | Function | - |  |
| onClick | Function | - |  |
| onContextmenu | Function | - |  |
| onGotpointercapture | Function | - |  |
| onLostpointercapture | Function | - |  |
| onPointerdown | Function | - |  |
| onPointermove | Function | - |  |
| onPointerup | Function | - |  |
| onPointercancel | Function | - |  |
| onPointerenter | Function | - |  |
| onPointerleave | Function | - |  |
| onPointerover | Function | - |  |
| onPointerout | Function | - |  |
| onBeforetoggle | Function | - |  |
| onToggle | Function | - |  |
| onWheel | Function | - |  |
| onAnimationcancel | Function | - |  |
| onAnimationstart | Function | - |  |
| onAnimationend | Function | - |  |
| onAnimationiteration | Function | - |  |
| onSecuritypolicyviolation | Function | - |  |
| onTransitioncancel | Function | - |  |
| onTransitionend | Function | - |  |
| onTransitionrun | Function | - |  |
| onTransitionstart | Function | - |  |
| modelValue | any | - | Value of the component. |
| defaultValue | any | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | The name attribute for the element, typically used in form submissions. |
| mask | boolean | true | Whether the password is rendered as masked. Use  `v-model:mask`  to make it two-way bindable. |
| size | any | - | Defines the size of the component. |
| invalid | null \| boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| variant | any | null | Specifies the input variant of the component. |
| fluid | null \| boolean | null | Spans 100% width of the container when enabled. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputPasswordPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| pcInputText | any | Used to pass attributes to the InputText component. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputpassword | Class name of the root element |
