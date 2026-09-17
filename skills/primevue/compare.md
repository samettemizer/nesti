# Compare

Compare two items side by side with a slider.

## Basic

Compare is composed with Compare as the root, two CompareItem layers, and a CompareHandle containing the keyboard-accessible CompareIndicator .

```vue
<template>
    <Compare class="aspect-video w-full max-w-lg">
        <CompareItem position="before">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island2.jpg" alt="Before" />
        </CompareItem>
        <CompareItem position="after">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island1.jpg" alt="After" />
        </CompareItem>
        <CompareHandle>
            <CompareIndicator class="group flex items-center justify-center">
                <ArrowsH class="group-data-[orientation=vertical]:rotate-90" />
            </CompareIndicator>
        </CompareHandle>
    </Compare>
</template>
```

## Custom Handle

The handle can be styled freely — give the indicator a rounded background, custom icon, and shadow for a more prominent look.

```vue
<template>
    <Compare class="aspect-video max-w-lg mx-auto">
        <CompareItem position="before">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island2.jpg" />
        </CompareItem>
        <CompareItem position="after">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island1.jpg" />
        </CompareItem>
        <CompareHandle class="bg-transparent!">
            <CompareIndicator class="size-5! rounded-full! bg-white/50! transition-transform duration-200! hover:transform-[translate(-50%,-50%)_scale(1.5)]!" />
        </CompareHandle>
    </Compare>
</template>
```

## Hover

Enable slideOnHover to update the slider position by hovering over the component.

```vue
<template>
    <Compare class="aspect-video max-w-lg mx-auto" slideOnHover>
        <CompareItem position="before">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island2.jpg" />
        </CompareItem>
        <CompareItem position="after">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island1.jpg" />
        </CompareItem>
        <CompareHandle>
            <CompareIndicator class="group flex items-center justify-center">
                <Code class="group-data-[orientation=vertical]:rotate-90" />
            </CompareIndicator>
        </CompareHandle>
    </Compare>
</template>

<script setup>
import Code from '@primeicons/vue/code';
<\/script>
```

## Vertical

Set orientation to vertical for a vertical comparison layout.

```vue
<template>
    <Compare class="aspect-video max-w-lg mx-auto" orientation="vertical">
        <CompareItem position="before">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island2.jpg" />
        </CompareItem>
        <CompareItem position="after">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island1.jpg" />
        </CompareItem>
        <CompareHandle>
            <CompareIndicator class="group flex items-center justify-center">
                <Code class="group-data-[orientation=vertical]:rotate-90" />
            </CompareIndicator>
        </CompareHandle>
    </Compare>
</template>

<script setup>
import Code from '@primeicons/vue/code';
<\/script>
```

## With Chart

Combine slideOnHover with controlled value for interactive chart reveals.

```vue
<template>
    <Compare v-model="value" class="aspect-video max-w-lg mx-auto" slideOnHover>
        <CompareItem position="before">
            <svg class="absolute h-full w-full" viewBox="0 0 644 189" fill="none" xmlns="http://www.w3.org/2000/svg">
                <g clip-path="url(#compare_chart_clip)">
                    <path
                        d="M0.5 118.499C0.5 118.499 82 102.999 113.5 89.4989C145 75.9989 188.444 87.7869 235 77.4989C272.684 69.1719 293.654 62.4939 329 46.9989C409.332 11.7849 479.5 86.5 510.5 78C541.5 69.5 635.951 0.848863 644 1.49886"
                        stroke="var(--p-primary-color)"
                        stroke-width="2"
                    />
                    <path
                        d="M113.5 89.5006C82 103.001 0.5 118.501 0.5 118.501V188.501H644V1.50065C635.951 0.850647 541.5 69.5 510.5 78C479.5 86.5 409.332 11.7866 329 47.0006C293.654 62.4956 272.684 69.1736 235 77.5006C188.444 87.7886 145 76.0006 113.5 89.5006Z"
                        fill="url(#compare_chart_gradient)"
                    />
                </g>
                <defs>
                    <clipPath id="compare_chart_clip">
                        <rect width="644" height="189" fill="white" />
                    </clipPath>
                    <linearGradient id="compare_chart_gradient" x1="322.25" x2="322.25" y1="1.477" y2="188.5" gradientUnits="userSpaceOnUse">
                        <stop stop-color="var(--p-primary-color)" stop-opacity="0.4" />
                        <stop offset="1" stop-color="var(--p-primary-color)" stop-opacity="0" />
                    </linearGradient>
                </defs>
            </svg>
        </CompareItem>
    </Compare>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Controlled

Bind the value with v-model when external UI needs to stay in sync with the slider.

```vue
<template>
    <Compare v-model="value" class="aspect-video w-full max-w-lg" aria-label="Compare images">
        <CompareItem position="before">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island2.jpg" alt="Before" />
        </CompareItem>
        <CompareItem position="after">
            <img src="https://primefaces.org/cdn/primevue/images/compare/island1.jpg" alt="After" />
        </CompareItem>
        <CompareHandle>
            <CompareIndicator class="flex items-center justify-center">
                <ArrowsH />
            </CompareIndicator>
        </CompareHandle>
    </Compare>
    <div class="flex w-full max-w-lg items-center justify-between gap-4">
        <Button severity="secondary" outlined @click="value = 25">25%</Button>
        <InputNumber v-model="value" inputClass="w-20 text-center" :min="0" :max="100" suffix="%" />
        <Button severity="secondary" outlined @click="value = 75">75%</Button>
    </div>
</template>
```

## Template

Compare is not limited to images — any content can be placed inside the items for creative comparisons.

```vue
<template>
    <Compare class="relative w-full max-w-md mx-auto h-[320px]">
        <CompareItem position="before">
            <div class="size-full bg-purple-100 dark:bg-purple-900/50 p-6 flex items-center justify-center">
                <div class="w-full max-w-xs rounded-xl border bg-white dark:bg-purple-900 border-purple-100 dark:border-purple-800 p-5 space-y-4">
                    <div class="flex items-start justify-between">
                        <div class="flex items-center gap-3">
                            <Avatar shape="circle" class="w-10 h-10">
                                <img class="filter hue-rotate-[260deg] saturate-150" src="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" />
                            </Avatar>
                            <div>
                                <div class="font-medium text-purple-950 dark:text-purple-50">Amy Elsner</div>
                                <div class="text-sm text-purple-600 dark:text-purple-400">Developer</div>
                            </div>
                        </div>
                        <Tag class="bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-200">Pro</Tag>
                    </div>
                    <div class="space-y-2">
                        <div class="flex justify-between text-sm">
                            <span class="text-purple-600 dark:text-purple-400">Storage</span>
                            <span class="text-purple-950 dark:text-purple-50">7.2 GB / 10 GB</span>
                        </div>
                        <ProgressBar :value="72" :showValue="false" class="h-2 [&_.p-progressbar-indicator]:bg-purple-500 [&_.p-progressbar-track]:bg-purple-100 dark:[&_.p-progressbar-track]:bg-purple-800" />
                    </div>
                    <div class="flex gap-2 pt-2">
                        <Button severity="help" class="flex-1">Upgrade</Button>
                        <Button severity="help" variant="outlined">Settings</Button>
                    </div>
                </div>
            </div>
        </CompareItem>
        <CompareItem position="after">
            <div class="size-full bg-primary-100 dark:bg-primary-900/50 p-6 flex items-center justify-center">
                <div class="w-full max-w-xs rounded-xl border bg-white dark:bg-primary-900 border-primary-100 dark:border-primary-800 p-5 space-y-4">
                    <div class="flex items-start justify-between">
                        <div class="flex items-center gap-3">
                            <Avatar shape="circle" class="w-10 h-10">
                                <img src="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" />
                            </Avatar>
                            <div>
                                <div class="font-medium text-primary-950 dark:text-primary-50">Amy Elsner</div>
                                <div class="text-sm text-primary-600 dark:text-primary-400">Developer</div>
                            </div>
                        </div>
                        <Tag class="bg-primary-100 dark:bg-primary-800 text-primary-700 dark:text-primary-200">Pro</Tag>
                    </div>
                    <div class="space-y-2">
                        <div class="flex justify-between text-sm">
                            <span class="text-primary-600 dark:text-primary-400">Storage</span>
                            <span class="text-primary-950 dark:text-primary-50">7.2 GB / 10 GB</span>
                        </div>
                        <ProgressBar :value="72" :showValue="false" class="h-2 [&_.p-progressbar-indicator]:bg-primary [&_.p-progressbar-track]:bg-primary-100 dark:[&_.p-progressbar-track]:bg-primary-800" />
                    </div>
                    <div class="flex gap-2 pt-2">
                        <Button class="flex-1">Upgrade</Button>
                        <Button variant="outlined">Settings</Button>
                    </div>
                </div>
            </div>
        </CompareItem>
        <CompareHandle>
            <CompareIndicator class="group flex items-center justify-center border border-surface">
                <Code class="group-data-[orientation=vertical]:rotate-90" />
            </CompareIndicator>
        </CompareHandle>
    </Compare>
</template>

<script setup>
import Code from '@primeicons/vue/code';
<\/script>
```

## Accessibility

Screen Reader Compare uses a hidden range input for keyboard accessibility. The input supports aria-label , aria-labelledby , aria-valuemin , aria-valuemax , and aria-valuenow attributes. Use arrow keys to adjust the slider position. Keyboard Support Key Function tab Moves focus to the component. left arrow up arrow Decrements the value. right arrow down arrow Increments the value. home Set the minimum value. end Set the maximum value. page up Increments the value by a browser-defined larger step (approximately 10% of the range). page down Decrements the value by a browser-defined larger step (approximately 10% of the range).

```vue
<template>
    <span id="compare_label">Compare Images</span>
    <Compare aria-labelledby="compare_label">...</Compare>

    <Compare aria-label="Compare Images">...</Compare>
</template>
```

## Compare API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | number | - | Value of the component. Pair with  `v-model`  for two-way binding. |
| min | number | 0 | Minimum boundary value. |
| max | number | 100 | Maximum boundary value. |
| step | number | 1 | Step factor to increment/decrement the value. |
| orientation | "horizontal" \| "vertical" | horizontal | Orientation of the compare slider. |
| slideOnHover | boolean | false | Whether the slider moves on hover. |
| disabled | boolean | false | Whether the component is disabled. |
| readonly | boolean | false | Whether the component is read-only. |
| invalid | boolean | false | When present, it specifies that the component should be invalid. |
| tabindex | number | - | The tab index of the hidden range input. |
| ariaLabel | string | - | Establishes a string value that labels the component. |
| ariaLabelledby | string | - | Establishes relationships between the component and label(s). |
| name | string | - | Name of the hidden input. |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ComparePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| item | ComparePassThroughOptionType | Used to pass attributes to CompareItem elements. |
| handle | ComparePassThroughOptionType | Used to pass attributes to CompareHandle element. |
| indicator | ComparePassThroughOptionType | Used to pass attributes to CompareIndicator element. |
| input | ComparePassThroughOptionType | Used to pass attributes to the hidden range input. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-compare | Class name of the root element. |
| p-compare-input | Class name of the hidden range input. |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| compare.border.radius | --p-compare-border-radius | Border radius of root |
| compare.handle.background | --p-compare-handle-background | Background of handle (track) |
| compare.handle.size | --p-compare-handle-size | Size of handle (thickness; width when vertical, height when horizontal) |
| compare.indicator.size | --p-compare-indicator-size | Size of indicator (square width and height) |
| compare.indicator.background | --p-compare-indicator-background | Background of indicator |
| compare.indicator.border.radius | --p-compare-indicator-border-radius | Border radius of indicator |
| compare.indicator.focus.ring.width | --p-compare-indicator-focus-ring-width | Focus ring width of indicator |
| compare.indicator.focus.ring.style | --p-compare-indicator-focus-ring-style | Focus ring style of indicator |
| compare.indicator.focus.ring.color | --p-compare-indicator-focus-ring-color | Focus ring color of indicator |
| compare.indicator.focus.ring.offset | --p-compare-indicator-focus-ring-offset | Focus ring offset of indicator |
| compare.indicator.icon.color | --p-compare-indicator-icon-color | Icon color of indicator |
| compare.indicator.icon.size | --p-compare-indicator-icon-size | Icon size of indicator |

## Compare Item API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| position | "before" \| "after" | before | Whether the item is before or after the handle. |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CompareItemPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-compare-item | Class name of the root element. |

## Compare Handle API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | SPAN | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CompareHandlePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-compare-handle | Class name of the root element. |

## Compare Indicator API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | SPAN | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| inputId | string | - | Id of the hidden input. |
| inputStyle | any | - | Inline style of the hidden input. |
| inputClass | any | - | Style class of the hidden input. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CompareIndicatorPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-compare-indicator | Class name of the root element. |
