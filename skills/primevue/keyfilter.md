# KeyFilter

KeyFilter is a directive to restrict individual key strokes. In order to restrict the whole input, use InputNumber or InputMask instead.

## Presets

KeyFilter provides various presets configured with the v-keyfilter directive.

```vue
<template>
    <div class="flex flex-wrap gap-4 mb-6">
        <div class="flex-auto">
            <Label for="integer" class="font-bold! block mb-2 "> Integer </Label>
            <InputText id="integer" v-model="integer" v-keyfilter.int class="w-full" />
        </div>
        <div class="flex-auto">
            <Label for="number" class="font-bold! block mb-2 "> Number </Label>
            <InputText id="number" v-model="number" v-keyfilter.num class="w-full" />
        </div>
        <div class="flex-auto">
            <Label for="money" class="font-bold! block mb-2 "> Money </Label>
            <InputText id="money" v-model="money" v-keyfilter.money class="w-full" />
        </div>
    </div>
    <div class="flex flex-wrap gap-4">
        <div class="flex-auto">
            <Label for="hex" class="font-bold! block mb-2 "> Hex </Label>
            <InputText id="hex" v-model="hex" v-keyfilter.hex class="w-full" />
        </div>
        <div class="flex-auto">
            <Label for="alphabetic" class="font-bold! block mb-2 "> Alphabetic </Label>
            <InputText id="alphabetic" v-model="alphabetic" v-keyfilter.alpha class="w-full" />
        </div>
        <div class="flex-auto">
            <Label for="alphanumeric" class="font-bold! block mb-2 "> Alphanumeric </Label>
            <InputText id="alphanumeric" v-model="alphanumeric" v-keyfilter.alphanum class="w-full" />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const integer = ref(null);
const number = ref(null);
const money = ref(null);
const hex = ref(null);
const alphabetic = ref(null);
const alphanumeric = ref(null);
<\/script>
```

## Regex

In addition to the presets, a regular expression can be configured for customization.

```vue
<template>
    <div class="flex flex-wrap gap-4">
        <div class="flex-auto">
            <label for="blockspace" class="text-sm font-bold block mb-2"> Block Space </label>
            <InputText id="blockspace" v-model="blockSpaceValue" v-keyfilter="blockSpace" class="w-full" />
        </div>
        <div class="flex-auto">
            <label for="block" class="text-sm font-bold block mb-2"> Block < > * ! </label>
            <InputText id="block" v-model="blockCharsValue" v-keyfilter="blockChars" class="w-full" />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const blockSpaceValue = ref(null);
const blockCharsValue = ref(null);
const blockSpace = /^[^\s]+$/;
const blockChars = /^[^<>*!]+$/;
<\/script>
```

## Regex Word

Validation against the whole input is available with the validateOnly option enabled so that the keys are allowed only when the resulting value matches the pattern.

```vue
<template>
    <div class="flex justify-center">
        <div>
            <Label for="numkeys" class="font-bold! block mb-2">Block Numeric (allow "+" only once at start)</Label>
            <InputText id="numkeys" v-model="text" v-keyfilter="blockNumeric" fluid />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const text = ref(null);
const blockNumeric = { pattern: /^[+]?(\\d{1,12})?$/, validateOnly: true };
<\/script>
```

## Accessibility

Refer to InputText for accessibility as KeyFilter is a built-in add-on of the InputText.

## Key Filter API

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | KeyFilterDirectivePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | DirectiveHooks<any, any> | Used to manage all lifecycle hooks. |

### Theming
