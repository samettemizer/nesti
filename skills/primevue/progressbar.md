# ProgressBar

ProgressBar is a process status indicator.

## Basic

Reflects the completion percentage of an ongoing process.

```vue
<template>
    <div class="max-w-sm mx-auto">
        <ProgressBar :value="50" />
    </div>
</template>
```

## Dynamic

Value is reactive so updating it dynamically changes the bar as well.

```vue
<template>
    <div class="max-w-sm mx-auto">
        <div class="text-color font-medium text-sm mb-2">Uploading Files</div>
        <ProgressBar :value="value" />
    </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';

const value = ref(0);
const interval = ref(null);

onMounted(() => {
    interval.value = setInterval(() => {
        const newValue = Math.round(value.value + Math.random() * 40 + 1);

        if (newValue >= 100) {
            value.value = 100;
            clearInterval(interval.value);
        } else {
            value.value = newValue;
        }
    }, 2000);
});

onBeforeUnmount(() => {
    if (interval.value) {
        clearInterval(interval.value);
    }
});
<\/script>
```

## Template

The displayed value can be formatted freely and the bar restyled through passthrough; here several bars share the same animated progress with different formatters.

```vue
<template>
    <div class="max-w-sm mx-auto space-y-8">
        <div>
            <div class="flex items-center justify-between mb-3 text-sm">
                <span class="font-medium">Basic Percentage</span>
                <span>{{ basicLabel }}</span>
            </div>
            <ProgressBar :value="percent" :showValue="false" :pt="{ root: 'h-1.5! rounded-full!', value: 'bg-blue-600! rounded-full!' }" />
        </div>

        <div>
            <div class="flex items-center justify-between mb-3 text-sm">
                <span class="font-medium">File Size Progress</span>
                <span>{{ fileSizeLabel }}</span>
            </div>
            <ProgressBar :value="percent" :showValue="false" :pt="{ root: 'h-1.5! rounded-full!', value: 'bg-emerald-600! rounded-full!' }" />
        </div>

        <div>
            <div class="flex items-center justify-between mb-3 text-sm">
                <span class="font-medium">Time Remaining</span>
                <span>{{ timeLabel }}</span>
            </div>
            <ProgressBar :value="percent" :showValue="false" :pt="{ root: 'h-1.5! rounded-full!', value: 'bg-purple-600! rounded-full!' }" />
        </div>

        <div>
            <div class="flex items-center justify-between mb-3 text-sm">
                <span class="font-medium">Upload Status Steps</span>
                <span>{{ statusLabel }}</span>
            </div>
            <ProgressBar :value="percent" :showValue="false" :pt="{ root: 'h-1.5! rounded-full!', value: 'bg-orange-600! rounded-full!' }" />
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

const uploadedFileSize = ref(0);
const maxFileSize = 5000;
let interval = null;

const percent = computed(() => (uploadedFileSize.value / maxFileSize) * 100);

const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes.toFixed(2) + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
    else return (bytes / 1048576).toFixed(2) + ' MB';
};

const basicLabel = computed(() => \`\${percent.value.toFixed(1)}%\`);
const fileSizeLabel = computed(() => \`\${formatFileSize((percent.value / 100) * maxFileSize)} / \${formatFileSize(maxFileSize)}\`);
const timeLabel = computed(() => {
    const remaining = ((maxFileSize - uploadedFileSize.value) / 200).toFixed(0);

    return \`\${percent.value.toFixed(0)}% (\${remaining}s remaining)\`;
});
const statusLabel = computed(() => {
    const v = percent.value;

    if (v < 40) return 'Preparing file...';
    else if (v < 60) return 'Uploading file...';
    else if (v < 99) return 'Finalizing...';
    else return 'Upload complete';
});

onMounted(() => {
    interval = setInterval(() => {
        const newValue = uploadedFileSize.value + Math.floor(Math.random() * 200) + 1;

        uploadedFileSize.value = newValue >= maxFileSize ? maxFileSize : newValue;
    }, 500);
});

onBeforeUnmount(() => clearInterval(interval));
<\/script>
```

## Indeterminate

For progresses with no value to track, set the mode property to indeterminate .

```vue
<template>
    <div class="max-w-sm mx-auto">
        <ProgressBar mode="indeterminate" :style="{ height: '6px' }" />
    </div>
</template>
```

## As Steps

Steps are used to display a progress with multiple steps.

```vue
<template>
    <div class="max-w-sm mx-auto">
        <div class="mb-3 font-medium text-sm">{{ orderProgress[step].status }}</div>
        <ProgressBar :value="stepValue" />
        <div class="flex items-center justify-between mt-6">
            <Button type="button" :rounded="true" variant="text" severity="contrast" @click="prevStep()" :disabled="step === 0">Previous</Button>
            <Button type="button" :rounded="true" variant="text" severity="contrast" @click="nextStep()" :disabled="step === orderProgress.length - 1">Next</Button>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const orderProgress = ref([{ status: 'Place Order' }, { status: 'Order Placed' }, { status: 'Processing' }, { status: 'Shipped' }, { status: 'Delivered' }]);
const step = ref(1);

const stepValue = computed(() => (step.value / (orderProgress.value.length - 1)) * 100);

const nextStep = () => {
    step.value = Math.min(step.value + 1, orderProgress.value.length - 1);
};

const prevStep = () => {
    step.value = Math.max(step.value - 1, 0);
};
<\/script>
```

## Accessibility

Screen Reader ProgressBar components uses progressbar role along with aria-valuemin , aria-valuemax and aria-valuenow attributes. Value to describe the component can be defined using aria-labelledby and aria-label props. Keyboard Support Not applicable.

```vue
<template>
    <span id="label_status">Status</span>
    <ProgressBar aria-labelledby="label_status" />

    <ProgressBar aria-label="Status" />
</template>
```

## Progress Bar API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | number | - | Current value of the progress. |
| mode | "indeterminate" \| "determinate" | determinate | Defines the mode of the progress |
| showValue | boolean | true | Whether to display the progress bar value. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ProgressBarPassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| value | ProgressBarPassThroughOptionType<T> | Used to pass attributes to the value's DOM element. |
| label | ProgressBarPassThroughOptionType<T> | Used to pass attributes to the label's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-progressbar | Class name of the root element |
| p-progressbar-value | Class name of the value element |
| p-progressbar-label | Class name of the label element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| progressbar.background | --p-progressbar-background | Background of root |
| progressbar.border.radius | --p-progressbar-border-radius | Border radius of root |
| progressbar.height | --p-progressbar-height | Height of root |
| progressbar.value.background | --p-progressbar-value-background | Background of value |
| progressbar.label.color | --p-progressbar-label-color | Color of label |
| progressbar.label.font.size | --p-progressbar-label-font-size | Font size of label |
| progressbar.label.font.weight | --p-progressbar-label-font-weight | Font weight of label |
