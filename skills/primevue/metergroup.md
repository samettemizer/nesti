# MeterGroup

MeterGroup displays scalar measurements within a known range.

## Basic

Visualizes multiple values as segmented horizontal bars.

```vue
<template>
    <MeterGroup :value="value" class="max-w-md mx-auto" />
</template>

<script setup>
import { ref } from "vue";

const value = ref([{ label: 'Space used', value: 15, color: 'var(--p-primary-color)' }]);
<\/script>
```

## Multiple

Adding more items to the value array displays the meters in a group.

```vue
<template>
    <MeterGroup :value="value" class="max-w-md mx-auto" />
</template>

<script setup>
import { ref } from "vue";

const value = ref([
    { label: 'Apps', value: 14, color: 'var(--p-violet-500)' },
    { label: 'Messages', value: 12, color: 'var(--p-emerald-500)' },
    { label: 'Media', value: 8, color: 'var(--p-amber-500)' },
    { label: 'System', value: 12, color: 'var(--p-blue-500)' },
    { label: 'Documents', value: 6, color: 'var(--p-gray-500)' },
    { label: 'Cache', value: 11, color: 'var(--p-cyan-500)' },
    { label: 'Other', value: 9, color: 'var(--p-pink-500)' }
]);
<\/script>
```

## Color

MeterGroup supports custom colors through the color property, which accepts CSS variables, hex, rgb, hsl or hsla values.

```vue
<template>
    <MeterGroup :value="value" class="max-w-md mx-auto" />
</template>

<script setup>
import { ref } from 'vue';

const value = ref([
    { label: 'Violet', value: 12, color: 'var(--p-violet-500)' },
    { label: 'Emerald', value: 14, color: '#10B981' },
    { label: 'Rose', value: 10, color: 'rgb(244, 63, 94)' },
    { label: 'Blue', value: 8, color: '#3B82F6' },
    { label: 'Yellow', value: 10, color: '#EAB308' }
]);
<\/script>
```

## Icon

Icons can be displayed next to the labels instead of the default marker.

```vue
<template>
    <MeterGroup :value="value" class="max-w-md mx-auto" />
</template>

<script setup>
import { ref } from 'vue';
import Cog from '@primeicons/vue/cog';
import Image from '@primeicons/vue/image';
import Inbox from '@primeicons/vue/inbox';
import Table from '@primeicons/vue/table';

const value = ref([
    { label: 'Apps', value: 16, color: 'var(--p-violet-500)', icon: Table  },
    { label: 'Messages', value: 8, color: 'var(--p-emerald-500)', icon: Inbox },
    { label: 'Media', value: 24, color: 'var(--p-amber-500)', icon: Image },
    { label: 'System', value: 10, color: 'var(--p-blue-500)', icon: Cog }
]);
<\/script>
```

## Label

The default orientation of the labels is horizontal, and the vertical alternative is available through the labelOrientation option.

```vue
<template>
    <MeterGroup :value="value" labelPosition="start" class="max-w-md mx-auto" />
</template>

<script setup>
import { ref } from "vue";

const value = ref([
    { label: 'Apps', value: 16, color: 'var(--p-violet-500)' },
    { label: 'Messages', value: 8, color: 'var(--p-emerald-500)' },
    { label: 'Media', value: 24, color: 'var(--p-amber-500)' },
    { label: 'System', value: 10, color: 'var(--p-blue-500)' }
]);
<\/script>
```

## Vertical

Layout of the MeterGroup is configured with the orientation property that accepts either horizontal or vertical as available options.

```vue
<template>
    <div class="flex justify-center">
        <MeterGroup :value="value" orientation="vertical" labelOrientation="vertical" :style="{ height: '360px' }" />
    </div>
</template>

<script setup>
import { ref } from "vue";

const value = ref([
    { label: 'Apps', value: 24, color: 'var(--p-violet-500)' },
    { label: 'Messages', value: 16, color: 'var(--p-emerald-500)' },
    { label: 'Media', value: 24, color: 'var(--p-amber-500)' },
    { label: 'System', value: 12, color: 'var(--p-blue-500)' }
]);
<\/script>
```

## Min Max

Boundaries are configured with the min and max values whose defaults are 0 and 100 respectively.

```vue
<template>
    <MeterGroup :value="value" :max="200" class="max-w-md mx-auto" />
</template>

<script setup>
import { ref } from "vue";

const value = ref([
    { label: 'Apps', value: 16, color: 'var(--p-violet-500)' },
    { label: 'Messages', value: 8, color: 'var(--p-emerald-500)' },
    { label: 'Media', value: 24, color: 'var(--p-amber-500)' },
    { label: 'System', value: 10, color: 'var(--p-blue-500)' }
]);
<\/script>
```

## Template

MeterGroup provides templating support for labels, meter items, and content around the meters.

```vue
<template>
    <MeterGroup :value="value" labelPosition="start" class="max-w-sm mx-auto">
        <template #label="{ value }">
            <div class="flex flex-wrap gap-4">
                <template v-for="val of value" :key="val.label">
                    <Card class="flex-1 border border-surface shadow-none">
                        <template #content>
                            <div class="flex justify-between gap-8">
                                <div class="flex flex-col gap-1">
                                    <span class="text-surface-500 dark:text-surface-400 text-sm">{{ val.label }}</span>
                                    <span class="font-bold text-lg">{{ val.value }}%</span>
                                </div>
                                <span class="w-8 h-8 rounded-full inline-flex justify-center items-center text-center" :style="{ backgroundColor: \`\${val.color1}\`, color: '#ffffff' }">
                                    <component :is="val.icon" />
                                </span>
                            </div>
                        </template>
                    </Card>
                </template>
            </div>
        </template>
        <template #meter="slotProps">
            <span :class="slotProps.class" :style="{ background: \`linear-gradient(to right, \${slotProps.value.color1}, \${slotProps.value.color2})\`, width: slotProps.size }" />
        </template>
        <template #start="{ totalPercent }">
            <div class="flex justify-between mt-4 mb-2 relative">
                <span class="text-sm">Storage</span>
                <span :style="{ width: totalPercent + '%' }" class="absolute text-right text-sm">{{ totalPercent }}%</span>
                <span class="font-medium text-sm">1TB</span>
            </div>
        </template>
        <template #end>
            <div class="flex justify-between mt-4">
                <Button variant="outlined" size="small">Manage Storage</Button>
                <Button size="small">Update Plan</Button>
            </div>
        </template>
    </MeterGroup>
</template>

<script setup>
import { ref } from "vue";
import Cog from '@primeicons/vue/cog';
import Image from '@primeicons/vue/image';
import Inbox from '@primeicons/vue/inbox';
import Table from '@primeicons/vue/table';

const value = ref([
    { label: 'Apps', color1: '#34d399', color2: '#fbbf24', value: 25, icon: Table },
    { label: 'Messages', color1: '#fbbf24', color2: '#60a5fa', value: 15, icon: Inbox },
    { label: 'Media', color1: '#60a5fa', color2: '#c084fc', value: 20, icon: Image },
    { label: 'System', color1: '#c084fc', color2: '#c084fc', value: 10, icon: Cog }
]);
<\/script>
```

## Accessibility

Screen Reader MeterGroup component uses meter role in addition to the aria-valuemin , aria-valuemax and aria-valuenow attributes. Value to describe the component can be defined using aria-labelledby prop. Keyboard Support Component does not include any interactive elements.

## Meter Group API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | MeterItem[] | - | Current value of the metergroup. |
| min | number | 0 | Mininum boundary value. |
| max | number | 100 | Maximum boundary value. |
| orientation | "horizontal" \| "vertical" | horizontal | Specifies the layout of the component, valid values are 'horizontal' and 'vertical'. |
| labelPosition | "start" \| "end" | end | Specifies the label position of the component, valid values are 'start' and 'end'. |
| labelOrientation | "horizontal" \| "vertical" | horizontal | Specifies the label orientation of the component, valid values are 'horizontal' and 'vertical'. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | MeterGroupPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| meters | MeterGroupPassThroughOptionType | Used to pass attributes to the meter container's DOM element. |
| meter | MeterGroupPassThroughOptionType | Used to pass attributes to the meter's DOM element. |
| labelList | MeterGroupPassThroughOptionType | Used to pass attributes to the label list's DOM element. |
| label | MeterGroupPassThroughOptionType | Used to pass attributes to the label list item's DOM element. |
| labelIcon | MeterGroupPassThroughOptionType | Used to pass attributes to the label icon type's DOM element. |
| labelMarker | MeterGroupPassThroughOptionType | Used to pass attributes to the label list type's DOM element. |
| labelText | MeterGroupPassThroughOptionType | Used to pass attributes to the label's DOM element. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-metergroup | Class name of the root element |
| p-metergroup-meters | Class name of the meters element |
| p-metergroup-meter | Class name of the meter element |
| p-metergroup-label-list | Class name of the label list element |
| p-metergroup-label | Class name of the label element |
| p-metergroup-label-icon | Class name of the label icon element |
| p-metergroup-label-marker | Class name of the label marker element |
| p-metergroup-label-text | Class name of the label text element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| metergroup.border.radius | --p-metergroup-border-radius | Border radius of root |
| metergroup.gap | --p-metergroup-gap | Gap of root |
| metergroup.meters.background | --p-metergroup-meters-background | Background of meters |
| metergroup.meters.size | --p-metergroup-meters-size | Size of meters |
| metergroup.label.gap | --p-metergroup-label-gap | Gap of label |
| metergroup.label.marker.size | --p-metergroup-label-marker-size | Size of label marker |
| metergroup.label.text.font.weight | --p-metergroup-label-text-font-weight | Font weight of label text |
| metergroup.label.text.font.size | --p-metergroup-label-text-font-size | Font size of label text |
| metergroup.label.icon.size | --p-metergroup-label-icon-size | Size of label icon |
| metergroup.label.list.vertical.gap | --p-metergroup-label-list-vertical-gap | Vertical gap of label list |
| metergroup.label.list.horizontal.gap | --p-metergroup-label-list-horizontal-gap | Horizontal gap of label list |
