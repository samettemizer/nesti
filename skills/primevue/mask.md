# Mask

Mask is a directive used to enter input in a certain format such as numeric, date, currency, email and phone.

## Basic

The v-mask directive is applied directly to an InputText or native input. The mask pattern can be passed as a string shorthand or as a full options object. Use v-model on the host input for two-way binding.

```vue
<template>
    <div class="flex justify-center">
        <InputText id="basic" v-model="value" v-mask="'99-999999'" placeholder="99-999999" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Format Patterns

Mask format can be a combination of the following definitions; a for alphabetic characters, 9 for numeric characters and * for alphanumberic characters. In addition, formatting characters like ( , ) , - are also accepted.

```vue
<template>
    <div class="flex flex-wrap gap-4">
        <div class="flex-auto">
            <Label for="ssn" class="font-bold! block mb-2">SSN</Label>
            <InputText id="ssn" v-model="value1" v-mask="'999-99-9999'" placeholder="999-99-9999" fluid />
        </div>

        <div class="flex-auto">
            <Label for="phone" class="font-bold! block mb-2">Phone</Label>
            <InputText id="phone" v-model="value2" v-mask="'(999) 999-9999'" placeholder="(999) 999-9999" fluid />
        </div>

        <div class="flex-auto">
            <Label for="serial" class="font-bold! block mb-2">Serial</Label>
            <InputText id="serial" v-model="value3" v-mask="'a*-999-a999'" placeholder="a*-999-a999" fluid />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref('');
const value2 = ref('');
const value3 = ref('');
<\/script>
```

## Optional

When the input does not complete the mask definition, it is cleared by default. Use autoClear option to control this behavior. In addition, ? is used to mark anything after the question mark optional.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <InputText v-model="value" v-mask="'(999) 999-9999? x99999'" placeholder="(999) 999-9999? x99999" />
        <span class="text-sm text-muted-color">Bound value: {{ value || '—' }}</span>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Slot Character

Default placeholder for a mask is the underscore character. It can be customized by passing a slotChar in the directive options object.

```vue
<template>
    <div class="flex justify-center">
        <InputText id="basic" v-model="value" v-mask="{ mask: '99/99/9999', slotChar: 'mm/dd/yyyy' }" placeholder="99/99/9999" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Unmask

The onChange callback is invoked on every value change with both the masked value and the rawValue without the mask formatting characters, so both can be accessed at the same time.

```vue
<template>
    <div class="flex flex-col items-center gap-2">
        <InputText v-model="value" v-mask="{ mask: '(999) 999-9999', onChange: onMaskChange }" placeholder="(999) 999-9999" />
        <span class="text-sm text-muted-color">Masked: {{ value || '—' }}</span>
        <span class="text-sm text-muted-color">Raw: {{ rawValue || '—' }}</span>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
const rawValue = ref('');

const onMaskChange = (e) => {
    rawValue.value = e.rawValue;
};
<\/script>
```

## AutoClear

When autoClear is set to false, the incomplete value is preserved on blur instead of being cleared.

```vue
<template>
    <div class="flex justify-center">
        <InputText v-model="value" v-mask="{ mask: '99-999999', autoClear: false }" placeholder="99-999999" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Forms

The v-mask directive integrates seamlessly with the PrimeVue Forms library when applied to a named InputText .

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4 w-full sm:w-56">
            <div class="flex flex-col gap-1">
                <InputText name="serialNumber" v-mask="'99-999999'" placeholder="99-999999" fluid />
                <Message v-if="$form.serialNumber?.invalid" severity="error" size="small" variant="simple">{{ $form.serialNumber.error?.message }}</Message>
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
    serialNumber: ''
});

const resolver = ref(zodResolver(
    z.object({
        serialNumber: z.string().min(1, { message: 'Serial number is required.' })
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

Screen Reader Mask directive is used with a native input element that implicitly includes any passed attribute. Value to describe the component can either be provided via label tag combined with id attribute or using aria-labelledby , aria-label attributes. Keyboard Support Key Function tab Moves focus to the input.

```vue
<template>
    <label for="date">Date</label>
    <InputText id="date" v-mask="'99/99/9999'" />

    <span id="phone">Phone</span>
    <InputText aria-labelledby="phone" v-mask="'(999) 999-9999'" />

    <InputText aria-label="Age" v-mask="'99'" />
</template>
```

## Mask API

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | MaskDirectivePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | DirectiveHooks<any, any> | Used to manage all lifecycle hooks. |

### Theming
